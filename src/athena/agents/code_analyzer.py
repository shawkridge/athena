"""CodeAnalyzerAgent - Autonomous code quality and optimization analysis.

This agent analyzes code for quality issues, anti-patterns, and optimization
opportunities. It runs autonomously during the session, learning coding styles
and providing actionable insights for code improvement.

The agent integrates with:
- MemoryCoordinator: Stores findings as semantic knowledge
- PatternExtractor: Extracts coding procedures and conventions
- WorkflowOrchestrator: Suggests refactoring and improvement tasks
"""

import logging
import re
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict

# Import coordinator base class
from .coordinator import AgentCoordinator
from ..orchestration.adaptive_agent import AdaptiveAgent

# Import core memory operations
from ..episodic.operations import remember as remember_event
from ..memory.operations import store as store_fact, search as search_facts
from ..graph.operations import add_entity as add_graph_entity
from ..core.database import Database

logger = logging.getLogger(__name__)


@dataclass
class CodeIssue:
    """Represents a detected code issue."""
    issue_type: str  # anti-pattern, optimization, style, complexity
    description: str
    line_number: Optional[int] = None
    file_path: Optional[str] = None
    severity: str = "medium"  # low, medium, high, critical
    suggestion: str = ""
    confidence: float = 0.8  # 0.0-1.0


@dataclass
class CodeMetrics:
    """Represents code metrics."""
    lines_of_code: int = 0
    cyclomatic_complexity: float = 0.0
    nesting_depth: int = 0
    avg_function_length: float = 0.0
    maintainability_index: float = 0.0
    test_coverage: float = 0.0


class CodeAnalyzerAgent(AgentCoordinator, AdaptiveAgent):
    """Autonomous code quality and optimization analyzer.

    Analyzes code for:
    - Syntax errors and anti-patterns
    - Optimization opportunities
    - Code style violations
    - Complexity metrics
    - Learning coding conventions

    Adaptive features:
    - Learns which analysis strategies work best
    - Chooses deep vs. quick analysis based on success rates
    - Tracks accuracy of pattern detection
    """

    # Common anti-patterns
    ANTI_PATTERNS = {
        "python": {
            "mutable_default_arg": {
                "pattern": r"def\s+\w+\([^)]*=\s*(\[\]|\{\}|set\(\))",
                "description": "Mutable default argument",
                "severity": "high",
                "suggestion": "Use None as default and create new instance in function",
            },
            "bare_except": {
                "pattern": r"except\s*:",
                "description": "Bare except clause catches all exceptions",
                "severity": "medium",
                "suggestion": "Catch specific exceptions instead",
            },
            "global_variable": {
                "pattern": r"^\s*global\s+\w+",
                "description": "Global variable usage",
                "severity": "medium",
                "suggestion": "Consider using function parameters or class attributes",
            },
            "mixed_tabs_spaces": {
                "pattern": r"(^\t+ |^ +\t)",
                "description": "Mixed tabs and spaces for indentation",
                "severity": "high",
                "suggestion": "Use consistent indentation (4 spaces recommended)",
            },
        },
        "javascript": {
            "var_declaration": {
                "pattern": r"\bvar\s+\w+",
                "description": "Using var instead of let/const",
                "severity": "medium",
                "suggestion": "Use let or const instead of var",
            },
            "unused_variable": {
                "pattern": r"\b(?:const|let|var)\s+(\w+)\s*=",
                "description": "Potentially unused variable",
                "severity": "low",
                "suggestion": "Remove unused variable or use underscore prefix",
            },
        },
    }

    # Optimization patterns
    OPTIMIZATIONS = {
        "loop_comprehension": {
            "pattern": r"for\s+\w+\s+in\s+.*:\s+\w+\.append",
            "description": "Loop that could use list comprehension",
            "impact": "Performance",
            "suggestion": "Use list comprehension for better performance",
        },
        "string_concat": {
            "pattern": r"\+.*\.join",
            "description": "String concatenation in loop",
            "impact": "Performance",
            "suggestion": "Use str.join() instead of concatenation",
        },
    }

    def __init__(self, db: Optional[Database] = None):
        """Initialize the Code Analyzer Agent.

        Args:
            db: Optional database for adaptive learning. If provided, enables learning.
        """
        super().__init__(
            agent_id="code-analyzer",
            agent_type="code-analyzer",
        )
        self.files_analyzed = 0
        self.issues_found = 0
        self.optimizations_suggested = 0
        self.learned_styles: Dict[str, Any] = {}

        # Initialize adaptive learning if database provided
        self._adaptive_enabled = db is not None
        if self._adaptive_enabled:
            AdaptiveAgent.__init__(self, agent_name="code-analyzer", db=db)

    async def analyze_code_changes(self, diff: str) -> Dict[str, Any]:
        """Analyze code changes from git diff.

        Args:
            diff: Git diff output

        Returns:
            Analysis results with issues and suggestions
        """
        logger.info("Analyzing code changes...")
        results = {
            "status": "success",
            "files_analyzed": 0,
            "issues": [],
            "optimizations": [],
            "style_violations": [],
            "metrics": {},
        }

        try:
            # Parse diff to extract changed lines
            files = self._parse_diff(diff)

            for file_path, changes in files.items():
                self.files_analyzed += 1
                file_results = await self._analyze_file(file_path, changes)

                if file_results["issues"]:
                    results["issues"].extend(file_results["issues"])
                    self.issues_found += len(file_results["issues"])

                if file_results["optimizations"]:
                    results["optimizations"].extend(file_results["optimizations"])
                    self.optimizations_suggested += len(file_results["optimizations"])

                if file_results["style_violations"]:
                    results["style_violations"].extend(file_results["style_violations"])

            results["files_analyzed"] = self.files_analyzed

            # Store analysis in memory
            if results["issues"] or results["optimizations"]:
                await remember_event(
                    content=f"Code analysis: {self.issues_found} issues, {self.optimizations_suggested} optimizations found",
                    tags=["code-analysis", "quality"],
                    source="agent:code-analyzer",
                    importance=0.7 if results["issues"] else 0.5,
                )

            logger.info(f"Analysis complete: {len(results['issues'])} issues, {len(results['optimizations'])} optimizations")

        except Exception as e:
            logger.error(f"Error analyzing code: {e}")
            results["status"] = "error"
            results["error"] = str(e)

        return results

    async def find_anti_patterns(self, code: str, language: str = "python") -> List[CodeIssue]:
        """Find common anti-patterns in code.

        Args:
            code: Code to analyze
            language: Programming language (python, javascript, etc.)

        Returns:
            List of detected anti-patterns
        """
        issues = []

        try:
            if language not in self.ANTI_PATTERNS:
                logger.warning(f"No anti-patterns defined for {language}")
                return issues

            patterns = self.ANTI_PATTERNS[language]

            for line_num, line in enumerate(code.split("\n"), 1):
                for pattern_name, pattern_def in patterns.items():
                    if re.search(pattern_def["pattern"], line):
                        issue = CodeIssue(
                            issue_type="anti-pattern",
                            description=pattern_def["description"],
                            line_number=line_num,
                            severity=pattern_def.get("severity", "medium"),
                            suggestion=pattern_def.get("suggestion", ""),
                            confidence=0.85,
                        )
                        issues.append(issue)

            logger.info(f"Found {len(issues)} anti-patterns in {language} code")

        except Exception as e:
            logger.error(f"Error finding anti-patterns: {e}")

        return issues

    async def suggest_optimizations(self, code: str, language: str = "python") -> List[Dict[str, Any]]:
        """Suggest code optimizations.

        Args:
            code: Code to analyze
            language: Programming language

        Returns:
            List of optimization suggestions with impact estimates
        """
        suggestions = []

        try:
            for opt_name, opt_def in self.OPTIMIZATIONS.items():
                if re.search(opt_def["pattern"], code):
                    suggestion = {
                        "optimization": opt_name,
                        "description": opt_def["description"],
                        "impact": opt_def["impact"],
                        "suggestion": opt_def["suggestion"],
                        "confidence": 0.8,
                    }
                    suggestions.append(suggestion)
                    self.optimizations_suggested += 1

            # Calculate complexity metrics
            complexity = self._calculate_complexity(code)
            if complexity > 10:
                suggestions.append({
                    "optimization": "reduce_complexity",
                    "description": f"High cyclomatic complexity ({complexity})",
                    "impact": "Maintainability",
                    "suggestion": "Consider breaking this into smaller functions",
                    "confidence": 0.9,
                })

            logger.info(f"Generated {len(suggestions)} optimization suggestions")

        except Exception as e:
            logger.error(f"Error suggesting optimizations: {e}")

        return suggestions

    async def extract_coding_style(self, code: str) -> Dict[str, Any]:
        """Learn coding style from code.

        Args:
            code: Code to analyze

        Returns:
            Learned style conventions
        """
        style = {
            "indentation": self._detect_indentation(code),
            "naming_convention": self._detect_naming_convention(code),
            "line_length": self._detect_line_length(code),
            "comment_style": self._detect_comment_style(code),
            "docstring_style": self._detect_docstring_style(code),
        }

        # Store learned style
        self.learned_styles.update(style)

        logger.info(f"Learned coding style: {style}")

        return style

    async def calculate_metrics(self, code: str) -> CodeMetrics:
        """Calculate code metrics.

        Args:
            code: Code to analyze

        Returns:
            CodeMetrics object with analysis results
        """
        metrics = CodeMetrics()

        try:
            lines = code.split("\n")
            metrics.lines_of_code = len([l for l in lines if l.strip()])
            metrics.cyclomatic_complexity = self._calculate_complexity(code)
            metrics.nesting_depth = self._calculate_nesting_depth(code)
            metrics.avg_function_length = self._calculate_avg_function_length(code)
            metrics.maintainability_index = self._calculate_maintainability_index(code)

            logger.info(f"Calculated metrics: LOC={metrics.lines_of_code}, CC={metrics.cyclomatic_complexity}")

        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")

        return metrics

    # Private helper methods

    def _parse_diff(self, diff: str) -> Dict[str, List[str]]:
        """Parse git diff into file -> changes mapping."""
        files = {}
        current_file = None

        for line in diff.split("\n"):
            if line.startswith("+++"):
                current_file = line[6:]
                files[current_file] = []
            elif current_file and (line.startswith("+") or line.startswith("-")):
                files[current_file].append(line[1:])

        return files

    async def _analyze_file(self, file_path: str, changes: List[str]) -> Dict[str, Any]:
        """Analyze a single file."""
        results = {
            "file": file_path,
            "issues": [],
            "optimizations": [],
            "style_violations": [],
        }

        # Determine language from file extension
        language = self._detect_language(file_path)
        if not language:
            return results

        code = "\n".join(changes)

        # Find anti-patterns
        anti_patterns = await self.find_anti_patterns(code, language)
        results["issues"] = [asdict(issue) for issue in anti_patterns]

        # Suggest optimizations
        optimizations = await self.suggest_optimizations(code, language)
        results["optimizations"] = optimizations

        # Extract style
        style = await self.extract_coding_style(code)
        if style:
            results["style"] = style

        return results

    def _detect_language(self, file_path: str) -> Optional[str]:
        """Detect programming language from file extension."""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".java": "java",
            ".cpp": "cpp",
            ".go": "go",
            ".rs": "rust",
        }
        for ext, lang in ext_map.items():
            if file_path.endswith(ext):
                return lang
        return None

    def _detect_indentation(self, code: str) -> str:
        """Detect indentation style (spaces vs tabs, width)."""
        lines = code.split("\n")
        for line in lines:
            if line and line[0] in (" ", "\t"):
                if line[0] == "\t":
                    return "tabs"
                spaces = len(line) - len(line.lstrip())
                if spaces % 4 == 0:
                    return "4-spaces"
                elif spaces % 2 == 0:
                    return "2-spaces"
        return "4-spaces"  # default

    def _detect_naming_convention(self, code: str) -> str:
        """Detect naming convention (snake_case, camelCase, etc.)."""
        snake_count = len(re.findall(r"_[a-z]", code))
        camel_count = len(re.findall(r"[a-z][A-Z]", code))

        if snake_count > camel_count * 2:
            return "snake_case"
        elif camel_count > snake_count * 2:
            return "camelCase"
        return "mixed"

    def _detect_line_length(self, code: str) -> int:
        """Detect average line length."""
        lines = code.split("\n")
        if not lines:
            return 80
        avg_length = sum(len(line) for line in lines) / len(lines)
        return int(avg_length)

    def _detect_comment_style(self, code: str) -> str:
        """Detect comment style."""
        if "#" in code:
            return "hash"
        elif "//" in code:
            return "double-slash"
        elif "/*" in code:
            return "block"
        return "unknown"

    def _detect_docstring_style(self, code: str) -> str:
        """Detect docstring style."""
        if '"""' in code:
            return "triple-quote"
        elif "'''" in code:
            return "triple-single"
        elif "///" in code:
            return "triple-slash"
        return "unknown"

    def _calculate_complexity(self, code: str) -> float:
        """Calculate cyclomatic complexity."""
        # Simple heuristic: count branching statements
        complexity = 1.0
        complexity += len(re.findall(r"\bif\b", code)) * 1
        complexity += len(re.findall(r"\belif\b", code)) * 1
        complexity += len(re.findall(r"\belse\b", code)) * 0.5
        complexity += len(re.findall(r"\bfor\b", code)) * 1
        complexity += len(re.findall(r"\bwhile\b", code)) * 1
        complexity += len(re.findall(r"\btry\b", code)) * 1
        complexity += len(re.findall(r"\bexcept\b", code)) * 0.5
        return min(complexity, 100.0)  # cap at 100

    def _calculate_nesting_depth(self, code: str) -> int:
        """Calculate maximum nesting depth."""
        max_depth = 0
        current_depth = 0

        for line in code.split("\n"):
            indent = len(line) - len(line.lstrip())
            depth = indent // 4  # assume 4-space indentation
            if depth > max_depth:
                max_depth = depth
            current_depth = depth

        return max_depth

    def _calculate_avg_function_length(self, code: str) -> float:
        """Calculate average function length."""
        # Find function definitions and their sizes
        functions = re.findall(r"def\s+\w+.*?(?=\ndef|\nclass|\Z)", code, re.DOTALL)
        if not functions:
            return 0.0

        total_lines = sum(len(f.split("\n")) for f in functions)
        return total_lines / len(functions)

    def _calculate_maintainability_index(self, code: str) -> float:
        """Calculate maintainability index (0-100).

        Higher is better. Based on code metrics.
        """
        # Simplified calculation
        lines = len(code.split("\n"))
        complexity = self._calculate_complexity(code)
        comments_ratio = len(re.findall(r"#|//|/\*", code)) / max(lines, 1)

        # Formula: 171 - 5.2*ln(effort) - 0.23*complexity - 16.2*ln(LOC) + 50*sqrt(2.46*comments)
        import math
        effort = complexity * max(lines, 1) / 100

        try:
            index = 171 - 5.2 * math.log(max(effort, 1))
            index -= 0.23 * complexity
            index -= 16.2 * math.log(max(lines, 1))
            index += 50 * math.sqrt(2.46 * comments_ratio)
            return max(0.0, min(100.0, index))
        except Exception:
            return 50.0  # default

    # Adaptive learning methods (from AdaptiveAgent)
    async def decide(self, context: dict) -> str:
        """Decide analysis strategy based on learning history.

        Strategies:
        - deep_analysis: Full anti-pattern detection, metrics, optimizations
        - quick_analysis: Only critical anti-patterns
        - style_check: Only style violations

        Uses success rates to pick the best strategy.
        """
        if not self._adaptive_enabled:
            return "deep_analysis"  # Default if no learning

        # Check success rates for each strategy
        deep_rate = self.tracker.get_success_rate(self.agent_name, "deep_analysis", time_window_hours=24)
        quick_rate = self.tracker.get_success_rate(self.agent_name, "quick_analysis", time_window_hours=24)

        # If deep analysis has high success rate, use it
        if deep_rate > 0.8:
            return "deep_analysis"
        # If quick analysis is faster and nearly as good
        elif quick_rate > 0.7:
            return "quick_analysis"
        # Default to deep
        else:
            return "deep_analysis"

    async def execute(self, decision: str, context: dict) -> Any:
        """Execute analysis with chosen strategy."""
        if decision == "quick_analysis":
            # Only check critical issues
            code = context.get('code', '')
            language = context.get('language', 'python')
            issues = await self.find_anti_patterns(code, language)
            return {'issues': [i for i in issues if i.severity == 'critical']}

        elif decision == "style_check":
            code = context.get('code', '')
            style = await self.extract_coding_style(code)
            return {'style': style}

        else:  # deep_analysis
            # Full analysis
            code = context.get('code', '')
            language = context.get('language', 'python')

            issues = await self.find_anti_patterns(code, language)
            optimizations = await self.suggest_optimizations(code, language)
            style = await self.extract_coding_style(code)
            metrics = await self.calculate_metrics(code)

            return {
                'issues': issues,
                'optimizations': optimizations,
                'style': style,
                'metrics': asdict(metrics)
            }

    async def _evaluate_outcome(self, result: Any, decision: str, context: dict) -> tuple[float, str]:
        """Evaluate analysis result quality."""
        if not result:
            return 0.0, 'failure'

        # Success if we found substantive analysis
        if isinstance(result, dict):
            issues_found = len(result.get('issues', []))
            if issues_found > 0:
                # Found real issues - high confidence
                return 0.9, 'success'
            elif result.get('style') or result.get('metrics'):
                # Found some analysis even if no issues
                return 0.7, 'success'

        return 0.5, 'partial'
