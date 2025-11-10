"""MCP handlers for Strategies 1, 3, 5 - Learning from history, errors, and patterns."""

import logging

logger = logging.getLogger(__name__)


def register_learning_tools(server):
    """Register learning tools with MCP server.

    Args:
        server: MCP server instance
    """

    @server.tool()
    def analyze_git_history(
        since_days: int = 90,
        focus_keywords: list = None,
    ) -> dict:
        """Analyze git history to understand architectural decisions and evolution.

        Strategy 5: Learn from past decisions to understand why things were designed the way they are.

        Args:
            since_days: Look back how many days (default: 90)
            focus_keywords: Keywords to focus on (e.g., ["refactor", "migration"])

        Returns:
            {
                "analysis_timestamp": str,
                "period_days": int,
                "total_commits": int,
                "decisions": [
                    {
                        "title": str,
                        "decision_maker": str,
                        "date": str,
                        "rationale": str,
                        "affected_files": [str],
                    }
                ],
                "patterns": [
                    {
                        "pattern_name": str,
                        "evolution_description": str,
                        "first_appeared": str,
                        "last_modified": str,
                    }
                ],
                "lessons_learned": [str],
                "insights": [str],
            }
        """
        try:
            from ..learning.git_analyzer import get_git_analyzer

            analyzer = get_git_analyzer()
            analysis = analyzer.analyze_history(since_days, focus_keywords)

            return analysis

        except Exception as e:
            logger.error(f"Git history analysis failed: {e}")
            return {"error": f"Analysis failed: {str(e)}"}

    @server.tool()
    def diagnose_error(
        error_type: str,
        message: str,
        stack_trace: str,
        context: dict = None,
    ) -> dict:
        """Diagnose an error to understand root cause and solution.

        Strategy 1: Learn from failures to prevent recurrence.

        Args:
            error_type: Type of error (e.g., "AttributeError", "ConnectionError")
            message: Error message
            stack_trace: Full stack trace
            context: Additional context (logs, variables, etc.)

        Returns:
            {
                "error_type": str,
                "root_cause": str,
                "affected_component": str,
                "severity": str,
                "reproduction_steps": [str],
                "solution": str,
                "prevention": str,
                "related_errors": [str],
            }
        """
        try:
            from ..learning.error_diagnostician import ErrorDiagnostician

            diagnostician = ErrorDiagnostician()
            diagnosed = diagnostician.diagnose(
                error_type,
                message,
                stack_trace,
                context,
            )

            return {
                "error_id": diagnosed.error_id,
                "error_type": diagnosed.error_type,
                "message": diagnosed.message,
                "root_cause": diagnosed.root_cause,
                "affected_component": diagnosed.affected_component,
                "severity": diagnosed.severity,
                "reproduction_steps": diagnosed.reproduction_steps,
                "solution": diagnosed.solution,
                "prevention": diagnosed.prevention,
                "related_errors": diagnosed.related_errors,
                "timestamp": diagnosed.timestamp,
            }

        except Exception as e:
            logger.error(f"Error diagnosis failed: {e}")
            return {"error": f"Diagnosis failed: {str(e)}"}

    @server.tool()
    def analyze_traceback(traceback_str: str) -> dict:
        """Analyze a Python traceback to extract key information.

        Args:
            traceback_str: Python traceback string

        Returns:
            {
                "error_type": str,
                "message": str,
                "file": str,
                "line": str,
                "full_trace": str,
            }
        """
        try:
            from ..learning.error_diagnostician import ErrorDiagnostician

            diagnostician = ErrorDiagnostician()
            analysis = diagnostician.analyze_traceback(traceback_str)

            return analysis

        except Exception as e:
            logger.error(f"Traceback analysis failed: {e}")
            return {"error": f"Analysis failed: {str(e)}"}

    @server.tool()
    def find_duplicate_code(
        code_snippet: str,
        codebase_files: list = None,
    ) -> dict:
        """Find duplicate or similar code in codebase.

        Strategy 3: Prevent duplication and find existing implementations.

        Args:
            code_snippet: Code snippet to find duplicates of
            codebase_files: Files to search (if None, searches all Python files)

        Returns:
            {
                "code_snippet_size": int,
                "duplicates_found": int,
                "locations": [
                    {
                        "file": str,
                        "similarity": float,
                        "suggestion": str,
                    }
                ],
                "recommendation": str,
            }
        """
        try:
            from ..learning.pattern_detector import PatternDetector

            detector = PatternDetector()

            # Use provided files or discover
            files = codebase_files or ["src/", "tests/"]

            duplicates = detector.find_duplicate_logic(code_snippet, files)

            return {
                "code_snippet_size": len(code_snippet),
                "duplicates_found": len(duplicates),
                "locations": duplicates,
                "recommendation": "Consider extracting to shared utility module"
                if duplicates
                else "No duplicates found",
            }

        except Exception as e:
            logger.error(f"Duplicate detection failed: {e}")
            return {"error": f"Detection failed: {str(e)}"}

    @server.tool()
    def find_similar_functions(
        function_code: str,
        codebase_files: list = None,
        similarity_threshold: float = 0.8,
    ) -> dict:
        """Find similar functions in codebase.

        Args:
            function_code: Code of function to find similar ones for
            codebase_files: Files to search
            similarity_threshold: Minimum similarity (0.0-1.0)

        Returns:
            {
                "function_name": str,
                "similar_found": int,
                "functions": [
                    {
                        "file": str,
                        "function": str,
                        "similarity": float,
                    }
                ],
                "suggestion": str,
            }
        """
        try:
            from ..learning.pattern_detector import PatternDetector

            detector = PatternDetector()

            # Extract function name
            import re
            match = re.search(r"def\s+(\w+)", function_code)
            func_name = match.group(1) if match else "unknown"

            files = codebase_files or ["src/", "tests/"]
            similar = detector.find_similar_functions(
                function_code,
                files,
                similarity_threshold,
            )

            return {
                "function_name": func_name,
                "similar_found": len(similar),
                "functions": similar,
                "suggestion": "These functions may be candidates for consolidation"
                if similar
                else "No similar functions found",
            }

        except Exception as e:
            logger.error(f"Similar function detection failed: {e}")
            return {"error": f"Detection failed: {str(e)}"}

    @server.tool()
    def detect_code_patterns(codebase_files: list) -> dict:
        """Detect code patterns and duplicates in codebase.

        Strategy 3: Find where code patterns are repeated.

        Args:
            codebase_files: Python files to analyze

        Returns:
            {
                "total_files": int,
                "patterns_found": int,
                "duplicate_groups": int,
                "patterns": [
                    {
                        "name": str,
                        "type": str,
                        "frequency": int,
                        "locations": [dict],
                    }
                ],
                "recommendations": [str],
            }
        """
        try:
            from ..learning.pattern_detector import PatternDetector

            detector = PatternDetector()
            analysis = detector.analyze_codebase(codebase_files)

            return {
                "total_files": analysis["total_files"],
                "patterns_found": analysis["patterns_found"],
                "duplicate_groups": analysis["duplicate_groups"],
                "patterns": [
                    {
                        "name": p.name,
                        "type": p.pattern_type,
                        "frequency": p.frequency,
                        "locations": p.locations,
                    }
                    for p in analysis.get("patterns", {}).values()
                ],
                "recommendations": analysis.get("recommendations", []),
            }

        except Exception as e:
            logger.error(f"Pattern detection failed: {e}")
            return {"error": f"Detection failed: {str(e)}"}

    @server.tool()
    def get_error_summary() -> dict:
        """Get summary of diagnosed errors and frequency trends.

        Returns:
            {
                "total_errors": int,
                "error_types": dict,
                "critical": int,
                "high": int,
                "most_common": str,
                "prevention_recommendations": [str],
            }
        """
        try:
            from ..learning.error_diagnostician import ErrorDiagnostician

            diagnostician = ErrorDiagnostician()
            summary = diagnostician.get_error_summary()
            recommendations = diagnostician.prevent_future_errors()

            return {
                **summary,
                "prevention_recommendations": recommendations,
            }

        except Exception as e:
            logger.error(f"Error summary failed: {e}")
            return {"error": f"Failed to get summary: {str(e)}"}

    @server.tool()
    def get_pattern_statistics() -> dict:
        """Get statistics about patterns found in codebase.

        Returns:
            {
                "total_patterns": int,
                "pattern_types": dict,
                "most_common_type": str,
                "duplicate_groups": int,
                "total_duplicate_instances": int,
            }
        """
        try:
            from ..learning.pattern_detector import PatternDetector

            detector = PatternDetector()
            stats = detector.get_pattern_statistics()

            return stats

        except Exception as e:
            logger.error(f"Pattern statistics failed: {e}")
            return {"error": f"Failed to get statistics: {str(e)}"}

    @server.tool()
    def get_architectural_decisions(
        since_days: int = 90,
        keywords: list = None,
    ) -> dict:
        """Get architectural decisions from git history.

        Strategy 5: Understand why architectural choices were made.

        Args:
            since_days: Look back how many days
            keywords: Filter by keywords (e.g., ["architecture", "refactor"])

        Returns:
            {
                "total_decisions": int,
                "decisions": [
                    {
                        "title": str,
                        "context": str,
                        "decision_maker": str,
                        "date": str,
                        "rationale": str,
                        "outcomes": [str],
                        "lessons": [str],
                    }
                ],
            }
        """
        try:
            from ..learning.git_analyzer import get_git_analyzer

            analyzer = get_git_analyzer()
            decisions = analyzer.find_architectural_decisions(keywords or [])

            return {
                "total_decisions": len(decisions),
                "decisions": [
                    {
                        "title": d.title,
                        "context": d.context,
                        "decision_maker": d.decision_maker,
                        "date": d.date,
                        "rationale": d.rationale,
                        "outcomes": d.outcomes,
                        "lessons": d.lessons_learned,
                        "affected_files": d.affected_files,
                    }
                    for d in decisions
                ],
            }

        except Exception as e:
            logger.error(f"Architectural decisions query failed: {e}")
            return {"error": f"Query failed: {str(e)}"}
