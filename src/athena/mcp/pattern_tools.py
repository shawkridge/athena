"""MCP tools for code pattern operations.

Exposes pattern learning, matching, and suggestion functionality via MCP:
- Extract patterns from git history
- Match patterns against current code
- Generate code improvement suggestions
- Track pattern effectiveness
"""

from typing import Any
from mcp.types import Tool

from ..core.database import Database
from ..procedural.pattern_extractor import PatternExtractor
from ..procedural.pattern_matcher import PatternMatcher
from ..procedural.pattern_suggester import PatternSuggester
from ..procedural.pattern_store import PatternStore


def get_pattern_tools() -> list[Tool]:
    """Get code pattern operation tools."""
    return [
        Tool(
            name="extract_refactoring_patterns",
            description="Extract refactoring patterns learned from git history",
            inputSchema={
                "type": "object",
                "properties": {
                    "lookback_days": {
                        "type": "integer",
                        "description": "How far back to analyze (default: 90)",
                        "default": 90,
                    },
                    "language": {
                        "type": "string",
                        "description": "Programming language to filter (default: python)",
                        "default": "python",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="extract_bug_fix_patterns",
            description="Extract bug-fix patterns from regression history",
            inputSchema={
                "type": "object",
                "properties": {
                    "lookback_days": {
                        "type": "integer",
                        "description": "How far back to analyze (default: 90)",
                        "default": 90,
                    },
                    "language": {
                        "type": "string",
                        "description": "Programming language to filter (default: python)",
                        "default": "python",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="suggest_refactorings",
            description="Suggest refactoring opportunities for code",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to code file",
                    },
                    "code_content": {
                        "type": "string",
                        "description": "Code content to analyze",
                    },
                    "language": {
                        "type": "string",
                        "description": "Programming language (default: python)",
                        "default": "python",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum suggestions (default: 5)",
                        "default": 5,
                    },
                },
                "required": ["file_path", "code_content"],
            },
        ),
        Tool(
            name="suggest_bug_fixes",
            description="Suggest applicable bug-fix patterns for an error",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to affected file",
                    },
                    "error_description": {
                        "type": "string",
                        "description": "Description of the error or symptoms",
                    },
                    "language": {
                        "type": "string",
                        "description": "Programming language (default: python)",
                        "default": "python",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum suggestions (default: 5)",
                        "default": 5,
                    },
                },
                "required": ["file_path", "error_description"],
            },
        ),
        Tool(
            name="detect_code_smells",
            description="Detect code quality issues (smells) in code",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to code file",
                    },
                    "code_content": {
                        "type": "string",
                        "description": "Code content to analyze",
                    },
                    "language": {
                        "type": "string",
                        "description": "Programming language (default: python)",
                        "default": "python",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum smells (default: 5)",
                        "default": 5,
                    },
                },
                "required": ["file_path", "code_content"],
            },
        ),
        Tool(
            name="get_pattern_suggestions",
            description="Get active pattern suggestions for a file",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to code file",
                    },
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="apply_suggestion",
            description="Mark a pattern suggestion as applied",
            inputSchema={
                "type": "object",
                "properties": {
                    "suggestion_id": {
                        "type": "integer",
                        "description": "ID of suggestion to apply",
                    },
                    "feedback": {
                        "type": "string",
                        "description": "Optional feedback on the suggestion",
                    },
                },
                "required": ["suggestion_id"],
            },
        ),
        Tool(
            name="dismiss_suggestion",
            description="Mark a pattern suggestion as dismissed (not applicable)",
            inputSchema={
                "type": "object",
                "properties": {
                    "suggestion_id": {
                        "type": "integer",
                        "description": "ID of suggestion to dismiss",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Optional reason for dismissal",
                    },
                },
                "required": ["suggestion_id"],
            },
        ),
        Tool(
            name="get_pattern_statistics",
            description="Get overall pattern suggestion statistics",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="get_pattern_effectiveness",
            description="Measure effectiveness of a pattern (applied vs dismissed)",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern_id": {
                        "type": "integer",
                        "description": "ID of pattern to measure",
                    },
                },
                "required": ["pattern_id"],
            },
        ),
        Tool(
            name="get_file_recommendations",
            description="Get comprehensive improvement recommendations for a file",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to code file",
                    },
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="get_pattern_library",
            description="Get summary of learned patterns by type",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern_type": {
                        "type": "string",
                        "description": "Type: refactoring, bug_fix, code_smell, architectural (default: all)",
                    },
                },
                "required": [],
            },
        ),
    ]


class PatternMCPHandlers:
    """Handler for pattern operation MCP tools."""

    def __init__(self, db: Database):
        """Initialize handlers."""
        self.db = db
        self.extractor = PatternExtractor(db)
        self.matcher = PatternMatcher(db)
        self.suggester = PatternSuggester(db)
        self.store = PatternStore(db)

    async def extract_refactoring_patterns(self, arguments: dict[str, Any]) -> str:
        """Handle extract_refactoring_patterns tool."""
        try:
            lookback_days = arguments.get("lookback_days", 90)
            language = arguments.get("language", "python")

            patterns = self.extractor.extract_refactoring_patterns(lookback_days, language)

            if not patterns:
                return f"✗ No refactoring patterns found in last {lookback_days} days"

            summary = f"✓ Extracted {len(patterns)} refactoring patterns\n\n"
            for pattern in patterns[:10]:
                summary += f"• {pattern.refactoring_type.value}: {pattern.description[:50]}\n"
                summary += f"  Frequency: {pattern.frequency}, Effectiveness: {pattern.effectiveness:.1%}\n"

            if len(patterns) > 10:
                summary += f"\n... and {len(patterns) - 10} more"

            return summary
        except Exception as e:
            return f"✗ Error extracting patterns: {str(e)}"

    async def extract_bug_fix_patterns(self, arguments: dict[str, Any]) -> str:
        """Handle extract_bug_fix_patterns tool."""
        try:
            lookback_days = arguments.get("lookback_days", 90)
            language = arguments.get("language", "python")

            patterns = self.extractor.extract_bug_fix_patterns(lookback_days, language)

            if not patterns:
                return f"✗ No bug-fix patterns found in last {lookback_days} days"

            summary = f"✓ Extracted {len(patterns)} bug-fix patterns\n\n"
            for pattern in patterns[:10]:
                summary += f"• {pattern.bug_type.value}: {pattern.description[:50]}\n"
                summary += f"  Confidence: {pattern.confidence:.1%}, Critical: {pattern.is_critical}\n"

            if len(patterns) > 10:
                summary += f"\n... and {len(patterns) - 10} more"

            return summary
        except Exception as e:
            return f"✗ Error extracting patterns: {str(e)}"

    async def suggest_refactorings(self, arguments: dict[str, Any]) -> str:
        """Handle suggest_refactorings tool."""
        try:
            file_path = arguments["file_path"]
            code_content = arguments["code_content"]
            language = arguments.get("language", "python")
            limit = arguments.get("limit", 5)

            suggestions = self.suggester.suggest_refactorings(
                file_path, code_content, language, limit
            )

            if not suggestions:
                return f"✓ No refactoring opportunities detected in {file_path}"

            summary = f"✓ Found {len(suggestions)} refactoring opportunities:\n\n"
            for suggestion in suggestions:
                summary += f"• {suggestion.reason}\n"
                summary += f"  Impact: {suggestion.impact}, Effort: {suggestion.effort}\n"
                summary += f"  Confidence: {suggestion.confidence:.1%}\n"

            return summary
        except Exception as e:
            return f"✗ Error analyzing code: {str(e)}"

    async def suggest_bug_fixes(self, arguments: dict[str, Any]) -> str:
        """Handle suggest_bug_fixes tool."""
        try:
            file_path = arguments["file_path"]
            error_description = arguments["error_description"]
            language = arguments.get("language", "python")
            limit = arguments.get("limit", 5)

            suggestions = self.suggester.suggest_bug_fixes(
                file_path, error_description, language, limit
            )

            if not suggestions:
                return f"✗ No applicable bug-fix patterns for this error"

            summary = f"✓ Found {len(suggestions)} applicable bug-fix patterns:\n\n"
            for suggestion in suggestions:
                summary += f"• {suggestion.reason}\n"
                summary += f"  Solution approach: {suggestion.effort} effort\n"
                summary += f"  Confidence: {suggestion.confidence:.1%}\n"

            return summary
        except Exception as e:
            return f"✗ Error analyzing error: {str(e)}"

    async def detect_code_smells(self, arguments: dict[str, Any]) -> str:
        """Handle detect_code_smells tool."""
        try:
            file_path = arguments["file_path"]
            code_content = arguments["code_content"]
            language = arguments.get("language", "python")
            limit = arguments.get("limit", 5)

            suggestions = self.suggester.suggest_code_smell_fixes(
                file_path, code_content, language, limit
            )

            if not suggestions:
                return f"✓ No code smells detected in {file_path}"

            summary = f"✓ Found {len(suggestions)} code quality issues:\n\n"
            for suggestion in suggestions:
                summary += f"• {suggestion.reason}\n"
                summary += f"  Impact: {suggestion.impact}, Effort to fix: {suggestion.effort}\n"
                summary += f"  Confidence: {suggestion.confidence:.1%}\n"

            return summary
        except Exception as e:
            return f"✗ Error analyzing code: {str(e)}"

    async def get_pattern_suggestions(self, arguments: dict[str, Any]) -> str:
        """Handle get_pattern_suggestions tool."""
        try:
            file_path = arguments["file_path"]

            suggestions = self.suggester.get_active_suggestions(file_path)

            if not suggestions:
                return f"✓ No pending suggestions for {file_path}"

            summary = f"✓ Found {len(suggestions)} active suggestions:\n\n"
            for suggestion in suggestions[:10]:
                summary += f"• ID {suggestion['id']}: {suggestion['reason']}\n"
                summary += f"  Confidence: {suggestion['confidence']:.1%}\n"

            if len(suggestions) > 10:
                summary += f"\n... and {len(suggestions) - 10} more"

            return summary
        except Exception as e:
            return f"✗ Error retrieving suggestions: {str(e)}"

    async def apply_suggestion(self, arguments: dict[str, Any]) -> str:
        """Handle apply_suggestion tool."""
        try:
            suggestion_id = arguments["suggestion_id"]
            feedback = arguments.get("feedback")

            success = self.suggester.apply_suggestion(suggestion_id, feedback)

            if success:
                return f"✓ Marked suggestion {suggestion_id} as applied"
            else:
                return f"✗ Suggestion {suggestion_id} not found"
        except Exception as e:
            return f"✗ Error applying suggestion: {str(e)}"

    async def dismiss_suggestion(self, arguments: dict[str, Any]) -> str:
        """Handle dismiss_suggestion tool."""
        try:
            suggestion_id = arguments["suggestion_id"]
            reason = arguments.get("reason")

            success = self.suggester.dismiss_suggestion(suggestion_id, reason)

            if success:
                return f"✓ Dismissed suggestion {suggestion_id}"
            else:
                return f"✗ Suggestion {suggestion_id} not found"
        except Exception as e:
            return f"✗ Error dismissing suggestion: {str(e)}"

    async def get_pattern_statistics(self, arguments: dict[str, Any]) -> str:
        """Handle get_pattern_statistics tool."""
        try:
            stats = self.suggester.get_suggestion_statistics()

            summary = "📊 Pattern Suggestion Statistics\n\n"
            summary += f"Total Suggestions: {stats['total_suggestions']}\n"
            summary += f"Applied: {stats['applied']} ({stats['overall_effectiveness']:.1%})\n"
            summary += f"Dismissed: {stats['dismissed']}\n"
            summary += f"Pending: {stats['pending']}\n\n"

            summary += "By Type:\n"
            for pattern_type, data in stats["by_type"].items():
                summary += (
                    f"• {pattern_type}: {data['count']} suggestions, "
                    f"{data['applied']} applied ({data['effectiveness']:.1%})\n"
                )

            return summary
        except Exception as e:
            return f"✗ Error retrieving statistics: {str(e)}"

    async def get_pattern_effectiveness(self, arguments: dict[str, Any]) -> str:
        """Handle get_pattern_effectiveness tool."""
        try:
            pattern_id = arguments["pattern_id"]

            metrics = self.suggester.measure_suggestion_effectiveness(pattern_id)

            summary = f"📈 Effectiveness of Pattern {pattern_id}\n\n"
            summary += f"Total Suggestions: {metrics['total_suggestions']}\n"
            summary += f"Applied: {metrics['applied_count']} ({metrics['effectiveness_rate']:.1%})\n"
            summary += f"Dismissed: {metrics['dismissed_count']} ({metrics['dismissal_rate']:.1%})\n"
            summary += f"Avg Confidence: {metrics['avg_confidence']:.1%}\n"

            return summary
        except Exception as e:
            return f"✗ Error measuring effectiveness: {str(e)}"

    async def get_file_recommendations(self, arguments: dict[str, Any]) -> str:
        """Handle get_file_recommendations tool."""
        try:
            file_path = arguments["file_path"]

            recommendations = self.suggester.get_file_improvement_recommendations(file_path)

            summary = f"📋 Improvement Recommendations for {file_path}\n\n"
            summary += f"Total Pending: {recommendations['total_pending_suggestions']}\n"
            summary += f"High Impact: {recommendations['high_impact_count']}\n"
            summary += f"Medium Impact: {recommendations['medium_impact_count']}\n"
            summary += f"Low Impact: {recommendations['low_impact_count']}\n"
            summary += f"Priority Score: {recommendations['priority_score']:.1f}\n"

            return summary
        except Exception as e:
            return f"✗ Error generating recommendations: {str(e)}"

    async def get_pattern_library(self, arguments: dict[str, Any]) -> str:
        """Handle get_pattern_library tool."""
        try:
            stats = self.store.get_statistics()

            summary = "📚 Learned Pattern Library\n\n"
            summary += f"Refactoring Patterns: {stats['total_refactoring_patterns']}\n"
            summary += f"Bug-Fix Patterns: {stats['total_bug_fix_patterns']}\n"
            summary += f"Code Smell Patterns: {stats['total_smell_patterns']}\n\n"

            summary += f"Total Applications: {stats['total_applications']}\n"
            summary += f"Successful: {stats['successful_applications']}\n"
            summary += f"Success Rate: {stats['application_success_rate']:.1%}\n"

            return summary
        except Exception as e:
            return f"✗ Error retrieving library: {str(e)}"
