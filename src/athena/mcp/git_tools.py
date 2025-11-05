"""MCP tools for git-aware temporal analysis.

Exposes git metadata, regression tracking, and author analysis through the memory system.
"""

from typing import Any
from mcp.types import Tool

from ..core.database import Database
from ..temporal.git_store import GitStore
from ..temporal.git_retrieval import GitTemporalRetrieval
from ..temporal.git_models import (
    GitMetadata,
    GitCommitEvent,
    GitFileChange,
    GitChangeType,
    RegressionAnalysis,
    RegressionType,
    AuthorMetrics,
    GitTemporalRelation,
    BranchMetrics,
)


def get_git_tools() -> list[Tool]:
    """Get git-aware temporal analysis tools."""
    return [
        Tool(
            name="record_git_commit",
            description="Record a git commit with metadata and file changes",
            inputSchema={
                "type": "object",
                "properties": {
                    "commit_hash": {"type": "string", "description": "Git commit SHA"},
                    "commit_message": {"type": "string", "description": "Commit message"},
                    "author": {"type": "string", "description": "Author name"},
                    "author_email": {"type": "string", "description": "Author email (optional)"},
                    "branch": {"type": "string", "description": "Branch name"},
                    "files_changed": {"type": "integer", "description": "Number of files"},
                    "insertions": {"type": "integer", "description": "Lines added"},
                    "deletions": {"type": "integer", "description": "Lines deleted"},
                    "event_id": {"type": "integer", "description": "Related episodic event ID (optional)"},
                    "is_merge": {"type": "boolean", "description": "Whether it's a merge commit"},
                    "is_release": {"type": "boolean", "description": "Whether it's a release"},
                },
                "required": ["commit_hash", "commit_message", "author", "branch"],
            },
        ),
        Tool(
            name="record_regression",
            description="Record a regression analysis linking bug to introducing commit",
            inputSchema={
                "type": "object",
                "properties": {
                    "regression_type": {
                        "type": "string",
                        "enum": [
                            "bug_introduction",
                            "perf_degradation",
                            "feature_breakage",
                            "test_failure",
                            "memory_leak",
                            "security_issue",
                        ],
                    },
                    "regression_description": {"type": "string"},
                    "introducing_commit": {"type": "string", "description": "Commit hash that caused it"},
                    "discovered_commit": {"type": "string", "description": "Commit where it was found"},
                    "fix_commit": {"type": "string", "description": "Fix commit (optional)"},
                    "impact_estimate": {"type": "number", "description": "0-1 impact severity"},
                    "confidence": {"type": "number", "description": "0-1 confidence in link"},
                    "affected_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Files affected by regression",
                    },
                },
                "required": [
                    "regression_type",
                    "regression_description",
                    "introducing_commit",
                    "discovered_commit",
                ],
            },
        ),
        Tool(
            name="when_was_introduced",
            description="Find when a regression was introduced",
            inputSchema={
                "type": "object",
                "properties": {
                    "commit_hash": {"type": "string", "description": "Commit hash to analyze"},
                },
                "required": ["commit_hash"],
            },
        ),
        Tool(
            name="who_introduced_regression",
            description="Find who introduced a regression with their metrics",
            inputSchema={
                "type": "object",
                "properties": {
                    "commit_hash": {"type": "string", "description": "Commit hash that introduced regression"},
                },
                "required": ["commit_hash"],
            },
        ),
        Tool(
            name="what_changed_since",
            description="Analyze what changed between regression introduction and fix",
            inputSchema={
                "type": "object",
                "properties": {
                    "regression_commit": {"type": "string"},
                    "fix_commit": {"type": "string", "description": "Optional fix commit"},
                    "lookback_hours": {"type": "integer", "description": "Hours to look back if no fix"},
                },
                "required": ["regression_commit"],
            },
        ),
        Tool(
            name="trace_regression_timeline",
            description="Create complete timeline from regression introduction to fix",
            inputSchema={
                "type": "object",
                "properties": {
                    "commit_hash": {"type": "string", "description": "Commit that introduced regression"},
                },
                "required": ["commit_hash"],
            },
        ),
        Tool(
            name="find_high_risk_commits",
            description="Find commits that introduced the most/highest-impact regressions",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max results", "default": 20},
                },
            },
        ),
        Tool(
            name="analyze_author_risk",
            description="Analyze regression patterns for a specific author",
            inputSchema={
                "type": "object",
                "properties": {
                    "author": {"type": "string", "description": "Author name to analyze"},
                },
                "required": ["author"],
            },
        ),
        Tool(
            name="get_regression_statistics",
            description="Get overall regression statistics by type and severity",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="get_file_history",
            description="Get complete history of a file including regressions",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "include_regressions": {"type": "boolean", "default": True},
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="get_commits_by_author",
            description="Get commits made by a specific author",
            inputSchema={
                "type": "object",
                "properties": {
                    "author": {"type": "string"},
                    "limit": {"type": "integer", "default": 100},
                },
                "required": ["author"],
            },
        ),
        Tool(
            name="get_commits_by_file",
            description="Get all commits that modified a specific file",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "limit": {"type": "integer", "default": 50},
                },
                "required": ["file_path"],
            },
        ),
    ]


class GitMCPHandlers:
    """Handlers for git-aware MCP tools."""

    def __init__(self, db: Database):
        """Initialize git MCP handlers."""
        self.db = db
        self.store = GitStore(db)
        self.retrieval = GitTemporalRetrieval(db)

    async def record_git_commit(self, arguments: dict[str, Any]) -> str:
        """Handle record_git_commit tool."""
        try:
            from datetime import datetime

            # Create git metadata
            git_metadata = GitMetadata(
                commit_hash=arguments["commit_hash"],
                commit_message=arguments["commit_message"],
                author=arguments["author"],
                author_email=arguments.get("author_email"),
                branch=arguments.get("branch", "main"),
                files_changed=arguments.get("files_changed", 0),
                insertions=arguments.get("insertions", 0),
                deletions=arguments.get("deletions", 0),
                parents=arguments.get("parents", []),
                committed_timestamp=datetime.now(),
            )

            # Create commit event
            commit_event = GitCommitEvent(
                git_metadata=git_metadata,
                event_id=arguments.get("event_id"),
                is_merge_commit=arguments.get("is_merge", False),
                is_release=arguments.get("is_release", False),
            )

            # Store it (handle UNIQUE constraint on commit_hash)
            try:
                commit_id, _ = self.store.create_commit_event(commit_event)
                return f"✓ Recorded commit {arguments['commit_hash'][:8]} (ID: {commit_id})"
            except Exception as e:
                if "UNIQUE constraint failed" in str(e):
                    # Commit already exists, just return success
                    return f"✓ Commit {arguments['commit_hash'][:8]} already recorded"
                raise

        except Exception as e:
            return f"✗ Error recording commit: {str(e)}"

    async def record_regression(self, arguments: dict[str, Any]) -> str:
        """Handle record_regression tool."""
        try:
            regression = RegressionAnalysis(
                regression_type=RegressionType(arguments["regression_type"]),
                regression_description=arguments["regression_description"],
                introducing_commit=arguments["introducing_commit"],
                discovered_commit=arguments["discovered_commit"],
                fix_commit=arguments.get("fix_commit"),
                affected_files=arguments.get("affected_files", []),
                affected_symbols=arguments.get("affected_symbols", []),
                impact_estimate=arguments.get("impact_estimate", 0.5),
                confidence=arguments.get("confidence", 0.5),
            )

            regression_id = self.store.record_regression(regression)
            return (
                f"✓ Recorded regression (ID: {regression_id}) "
                f"introduced in {arguments['introducing_commit'][:8]}"
            )

        except Exception as e:
            return f"✗ Error recording regression: {str(e)}"

    async def when_was_introduced(self, arguments: dict[str, Any]) -> str:
        """Handle when_was_introduced tool."""
        try:
            result = self.retrieval.when_was_introduced(arguments["commit_hash"])
            if not result:
                return f"✗ Commit {arguments['commit_hash'][:8]} not found"

            return (
                f"📅 Introduced: {result['when'].strftime('%Y-%m-%d %H:%M')}\n"
                f"👤 Author: {result['author']}\n"
                f"📝 Message: {result['message']}\n"
                f"📊 Changes: {result['insertions']} insertions, {result['deletions']} deletions"
            )

        except Exception as e:
            return f"✗ Error: {str(e)}"

    async def who_introduced_regression(self, arguments: dict[str, Any]) -> str:
        """Handle who_introduced_regression tool."""
        try:
            result = self.retrieval.who_introduced_regression(arguments["commit_hash"])
            if not result:
                return f"✗ Commit {arguments['commit_hash'][:8]} not found"

            metrics = result.get("metrics", {})
            return (
                f"👤 {result['author']} ({result.get('email', 'unknown')})\n"
                f"🔗 Commit: {result['commit_hash'][:8]}\n"
                f"📅 When: {result['when'].strftime('%Y-%m-%d %H:%M')}\n"
                f"📊 Their stats: {metrics.get('commits_count', 0)} commits, "
                f"{metrics.get('regressions_introduced', 0)} regressions introduced"
            )

        except Exception as e:
            return f"✗ Error: {str(e)}"

    async def what_changed_since(self, arguments: dict[str, Any]) -> str:
        """Handle what_changed_since tool."""
        try:
            result = self.retrieval.what_changed_since(
                arguments["regression_commit"],
                arguments.get("fix_commit"),
                arguments.get("lookback_hours", 24),
            )

            if "error" in result:
                return f"✗ {result['error']}"

            return (
                f"🔍 Changes between regression and fix:\n"
                f"📈 {result['total_commits']} commits, "
                f"{result['total_changes']} total lines changed\n"
                f"📁 {len(result['affected_files'])} files affected\n"
                f"⏱️  Timeframe: {result['intro_timestamp'].strftime('%Y-%m-%d')} to "
                f"{result['fix_timestamp'].strftime('%Y-%m-%d')}"
            )

        except Exception as e:
            return f"✗ Error: {str(e)}"

    async def trace_regression_timeline(self, arguments: dict[str, Any]) -> str:
        """Handle trace_regression_timeline tool."""
        try:
            result = self.retrieval.trace_regression_timeline(arguments["commit_hash"])

            if result["regressions_found"] == 0:
                return f"✗ No regressions found for commit {arguments['commit_hash'][:8]}"

            timeline_str = f"📊 Timeline ({result['regressions_found']} regression(s)):\n\n"
            for item in result["timeline"]:
                timeline_str += (
                    f"• {item['description']}\n"
                    f"  Type: {item['type']}\n"
                    f"  Introduced: {item['introduced'].strftime('%Y-%m-%d') if item['introduced'] else 'unknown'}\n"
                    f"  Discovered: {item['discovered'].strftime('%Y-%m-%d') if item['discovered'] else 'unknown'}\n"
                    f"  Fixed: {item['fixed'].strftime('%Y-%m-%d') if item['fixed'] else 'not yet'}\n"
                    f"  Impact: {item['impact']:.1f}, Confidence: {item['confidence']:.1f}\n\n"
                )

            return timeline_str.strip()

        except Exception as e:
            return f"✗ Error: {str(e)}"

    async def find_high_risk_commits(self, arguments: dict[str, Any]) -> str:
        """Handle find_high_risk_commits tool."""
        try:
            limit = arguments.get("limit", 20)
            results = self.retrieval.find_high_risk_commits(limit)

            if not results:
                return "✓ No high-risk commits found"

            output = f"🚨 High-Risk Commits ({len(results)}):\n\n"
            for i, commit in enumerate(results, 1):
                output += (
                    f"{i}. {commit['commit_hash'][:8]} by {commit['author']}\n"
                    f"   Message: {commit['message'][:50]}...\n"
                    f"   Regressions: {commit['regression_count']}, "
                    f"Max Impact: {commit['max_impact']:.1f}\n\n"
                )

            return output.strip()

        except Exception as e:
            return f"✗ Error: {str(e)}"

    async def analyze_author_risk(self, arguments: dict[str, Any]) -> str:
        """Handle analyze_author_risk tool."""
        try:
            result = self.retrieval.analyze_author_risk(arguments["author"])

            return (
                f"👤 {result['author']}\n"
                f"📊 Commits: {result['total_commits']}\n"
                f"🚨 Regressions introduced: {result['regressions_introduced']}\n"
                f"📈 Regression rate: {result['regression_rate']:.1%}\n"
                f"⚠️  Avg impact: {result['avg_impact']:.1f}"
            )

        except Exception as e:
            return f"✗ Error: {str(e)}"

    async def get_regression_statistics(self, arguments: dict[str, Any]) -> str:
        """Handle get_regression_statistics tool."""
        try:
            result = self.retrieval.get_regression_statistics()

            output = (
                f"📊 Regression Statistics:\n"
                f"Total: {result['total_regressions']}\n"
                f"Fixed: {result['total_fixed']} ({result['overall_fix_rate']:.1%})\n"
                f"Avg Impact: {result['avg_impact']:.1f}\n\n"
                f"By Type:\n"
            )

            for reg_type, stats in result["by_type"].items():
                output += (
                    f"• {reg_type}: {stats['count']} "
                    f"({stats['fix_rate']:.1%} fixed, "
                    f"avg impact {stats['avg_impact']:.1f})\n"
                )

            return output.strip()

        except Exception as e:
            return f"✗ Error: {str(e)}"

    async def get_file_history(self, arguments: dict[str, Any]) -> str:
        """Handle get_file_history tool."""
        try:
            result = self.retrieval.get_file_history(
                arguments["file_path"],
                arguments.get("include_regressions", True),
            )

            output = (
                f"📁 {result['file_path']}\n"
                f"📝 Total commits: {result['total_commits']}\n"
            )

            if result["related_regressions"]:
                output += f"🚨 Related regressions: {len(result['related_regressions'])}\n"
                for reg in result["related_regressions"][:5]:
                    output += f"  • {reg['description']}\n"

            return output.strip()

        except Exception as e:
            return f"✗ Error: {str(e)}"

    async def get_commits_by_author(self, arguments: dict[str, Any]) -> str:
        """Handle get_commits_by_author tool."""
        try:
            commits = self.store.get_commits_by_author(
                arguments["author"],
                arguments.get("limit", 100),
            )

            if not commits:
                return f"✗ No commits found for {arguments['author']}"

            output = f"📝 Commits by {arguments['author']} ({len(commits)}):\n\n"
            for commit in commits[:10]:
                output += (
                    f"• {commit['commit_hash'][:8]} "
                    f"({commit['committed_timestamp'].strftime('%Y-%m-%d')})\n"
                    f"  {commit['commit_message'][:60]}...\n\n"
                )

            return output.strip()

        except Exception as e:
            return f"✗ Error: {str(e)}"

    async def get_commits_by_file(self, arguments: dict[str, Any]) -> str:
        """Handle get_commits_by_file tool."""
        try:
            commits = self.store.get_commits_by_file(
                arguments["file_path"],
                arguments.get("limit", 50),
            )

            if not commits:
                return f"✗ No commits found for {arguments['file_path']}"

            output = f"📝 Commits for {arguments['file_path']} ({len(commits)}):\n\n"
            for commit in commits[:10]:
                output += (
                    f"• {commit['commit_hash'][:8]} by {commit['author']} "
                    f"({commit['change_type']})\n"
                    f"  {commit['commit_message'][:50]}...\n\n"
                )

            return output.strip()

        except Exception as e:
            return f"✗ Error: {str(e)}"
