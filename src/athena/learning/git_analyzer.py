"""Strategy 5: Git History Analysis - Learn from past decisions and architecture evolution.

Extract decision context, understand why changes were made, prevent repeating mistakes.
"""

import logging
import subprocess
import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CommitInfo:
    """Information about a git commit."""
    sha: str
    author: str
    date: str
    message: str
    files_changed: List[str]
    additions: int
    deletions: int
    is_merge: bool = False


@dataclass
class ArchitecturalDecision:
    """A significant architectural decision from git history."""
    decision_id: str
    title: str
    description: str
    context: str
    decision_maker: str
    date: str
    commit_sha: str
    affected_files: List[str]
    rationale: str
    outcomes: List[str]
    lessons_learned: List[str]


@dataclass
class PatternEvolution:
    """How a code pattern evolved over time."""
    pattern_name: str
    first_appeared: str
    last_modified: str
    commits: List[CommitInfo]
    evolution_description: str
    current_status: str


class GitAnalyzer:
    """Analyzes git history to learn from past decisions."""

    def __init__(self, repo_path: str = "."):
        """Initialize git analyzer.

        Args:
            repo_path: Path to git repository (default: current directory)
        """
        self.repo_path = repo_path
        self.cache: Dict[str, Any] = {}

    def analyze_history(
        self,
        since_days: int = 90,
        focus_keywords: List[str] = None,
    ) -> Dict[str, Any]:
        """Analyze git history for decisions and patterns.

        Args:
            since_days: Look back how many days (default: 90)
            focus_keywords: Keywords to focus on (e.g., ["refactor", "migration"])

        Returns:
            Analysis with decisions, patterns, and lessons learned
        """
        logger.info(f"Analyzing git history for last {since_days} days")

        try:
            # Get commit log
            commits = self._get_commits(since_days)
            logger.info(f"Found {len(commits)} commits")

            # Extract architectural decisions
            decisions = self._extract_decisions(commits, focus_keywords)
            logger.info(f"Identified {len(decisions)} architectural decisions")

            # Analyze patterns
            patterns = self._analyze_patterns(commits)
            logger.info(f"Found {len(patterns)} pattern evolutions")

            # Generate insights
            insights = self._generate_insights(commits, decisions, patterns)

            return {
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "period_days": since_days,
                "total_commits": len(commits),
                "decisions": decisions,
                "patterns": patterns,
                "insights": insights,
                "lessons_learned": self._extract_lessons(commits),
            }

        except Exception as e:
            logger.error(f"Error analyzing git history: {e}")
            return {
                "error": str(e),
                "period_days": since_days,
            }

    def get_file_history(self, filename: str, limit: int = 10) -> List[CommitInfo]:
        """Get commit history for a specific file.

        Args:
            filename: File path to analyze
            limit: Maximum number of commits to retrieve

        Returns:
            List of commits affecting this file
        """
        try:
            cmd = [
                "git",
                "log",
                f"--max-count={limit}",
                "--format=%H|%an|%ai|%s|%b",
                "--",
                filename,
            ]

            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10,
            )

            commits = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("|", 4)
                if len(parts) >= 4:
                    commits.append(
                        CommitInfo(
                            sha=parts[0][:8],
                            author=parts[1],
                            date=parts[2],
                            message=parts[3],
                            files_changed=[filename],
                            additions=0,
                            deletions=0,
                        )
                    )

            return commits

        except Exception as e:
            logger.warning(f"Error getting history for {filename}: {e}")
            return []

    def blame_file(self, filename: str) -> Dict[str, Any]:
        """Get blame information for understanding file ownership.

        Args:
            filename: File to blame

        Returns:
            Blame information with authors and lines
        """
        try:
            cmd = ["git", "blame", "--line-porcelain", filename]

            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10,
            )

            blame_data = {
                "file": filename,
                "authors": {},
                "lines_by_author": {},
            }

            for line in result.stdout.split("\n"):
                if not line or line.startswith("\t"):
                    continue
                parts = line.split()
                if len(parts) > 1 and parts[0].startswith("author"):
                    author = " ".join(parts[1:])
                    blame_data["authors"][author] = blame_data["authors"].get(author, 0) + 1

            return blame_data

        except Exception as e:
            logger.warning(f"Error blaming file {filename}: {e}")
            return {"file": filename, "error": str(e)}

    def find_architectural_decisions(
        self,
        patterns: List[str] = None,
    ) -> List[ArchitecturalDecision]:
        """Find significant architectural decisions in history.

        Args:
            patterns: Patterns to match (e.g., ["refactor", "architecture", "migration"])

        Returns:
            List of architectural decisions
        """
        patterns = patterns or [
            "refactor",
            "architecture",
            "migration",
            "redesign",
            "restructure",
        ]

        try:
            commits = self._get_commits(90)
            decisions = []

            for commit in commits:
                # Check if commit message contains decision patterns
                message_lower = commit.message.lower()

                if any(pattern in message_lower for pattern in patterns):
                    decision = ArchitecturalDecision(
                        decision_id=commit.sha,
                        title=commit.message.split("\n")[0],
                        description="\n".join(commit.message.split("\n")[1:]),
                        context=f"Commit {commit.sha} by {commit.author}",
                        decision_maker=commit.author,
                        date=commit.date,
                        commit_sha=commit.sha,
                        affected_files=commit.files_changed,
                        rationale=self._extract_rationale(commit.message),
                        outcomes=self._extract_outcomes(commit),
                        lessons_learned=self._extract_lessons_from_commit(commit),
                    )
                    decisions.append(decision)

            return decisions

        except Exception as e:
            logger.error(f"Error finding decisions: {e}")
            return []

    def _get_commits(self, since_days: int) -> List[CommitInfo]:
        """Get commits from the last N days."""
        try:
            cmd = [
                "git",
                "log",
                f"--since={since_days}.days.ago",
                "--format=%H|%an|%ai|%s|%b",
                "--numstat",
            ]

            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30,
            )

            commits = []
            current_commit = None

            for line in result.stdout.split("\n"):
                if not line:
                    continue

                # Commit header line
                if "|" in line and len(line.split("|")) >= 4:
                    if current_commit:
                        commits.append(current_commit)

                    parts = line.split("|", 4)
                    current_commit = CommitInfo(
                        sha=parts[0][:8],
                        author=parts[1],
                        date=parts[2],
                        message=parts[3],
                        files_changed=[],
                        additions=0,
                        deletions=0,
                    )
                # Stats line (additions deletions filename)
                elif current_commit and line[0].isdigit():
                    parts = line.split()
                    if len(parts) >= 3:
                        try:
                            current_commit.additions += int(parts[0])
                            current_commit.deletions += int(parts[1])
                            current_commit.files_changed.append(parts[2])
                        except ValueError:
                            pass

            if current_commit:
                commits.append(current_commit)

            return commits

        except Exception as e:
            logger.error(f"Error getting commits: {e}")
            return []

    def _extract_decisions(
        self,
        commits: List[CommitInfo],
        focus_keywords: List[str],
    ) -> List[ArchitecturalDecision]:
        """Extract architectural decisions from commits."""
        decisions = []

        keywords = focus_keywords or [
            "refactor",
            "architecture",
            "migration",
            "redesign",
        ]

        for commit in commits:
            if any(kw in commit.message.lower() for kw in keywords):
                decision = ArchitecturalDecision(
                    decision_id=commit.sha,
                    title=commit.message.split("\n")[0],
                    description=commit.message,
                    context=f"Modified {len(commit.files_changed)} files",
                    decision_maker=commit.author,
                    date=commit.date,
                    commit_sha=commit.sha,
                    affected_files=commit.files_changed,
                    rationale=self._extract_rationale(commit.message),
                    outcomes=[
                        f"Added {commit.additions} lines",
                        f"Removed {commit.deletions} lines",
                        f"Changed {len(commit.files_changed)} files",
                    ],
                    lessons_learned=self._extract_lessons_from_commit(commit),
                )
                decisions.append(decision)

        return decisions

    def _analyze_patterns(self, commits: List[CommitInfo]) -> List[PatternEvolution]:
        """Analyze how code patterns evolved."""
        patterns = {}

        # Group commits by files to track patterns
        file_history = {}
        for commit in commits:
            for filename in commit.files_changed:
                if filename not in file_history:
                    file_history[filename] = []
                file_history[filename].append(commit)

        # Create pattern evolutions
        pattern_list = []
        for filename, commits_list in list(file_history.items())[:10]:  # Top 10 patterns
            if commits_list:
                pattern = PatternEvolution(
                    pattern_name=filename,
                    first_appeared=commits_list[-1].date,
                    last_modified=commits_list[0].date,
                    commits=commits_list,
                    evolution_description=f"File has been modified {len(commits_list)} times",
                    current_status="active" if commits_list[0] else "archived",
                )
                pattern_list.append(pattern)

        return pattern_list

    def _generate_insights(
        self,
        commits: List[CommitInfo],
        decisions: List[ArchitecturalDecision],
        patterns: List[PatternEvolution],
    ) -> List[str]:
        """Generate insights from git history."""
        insights = []

        if commits:
            avg_commit_size = sum(c.additions + c.deletions for c in commits) / len(commits)
            insights.append(f"Average commit size: {avg_commit_size:.0f} lines")

        if decisions:
            insights.append(f"Found {len(decisions)} significant architectural decisions")

        # Most changed files
        file_changes = {}
        for commit in commits:
            for f in commit.files_changed:
                file_changes[f] = file_changes.get(f, 0) + 1

        if file_changes:
            most_changed = max(file_changes.items(), key=lambda x: x[1])
            insights.append(f"Most changed file: {most_changed[0]} ({most_changed[1]} times)")

        # Active developers
        authors = {}
        for commit in commits:
            authors[commit.author] = authors.get(commit.author, 0) + 1

        if authors:
            top_author = max(authors.items(), key=lambda x: x[1])
            insights.append(f"Most active developer: {top_author[0]} ({top_author[1]} commits)")

        return insights

    def _extract_rationale(self, message: str) -> str:
        """Extract rationale from commit message."""
        lines = message.split("\n")
        if len(lines) > 1:
            return lines[1]
        return ""

    def _extract_outcomes(self, commit: CommitInfo) -> List[str]:
        """Extract outcomes from commit."""
        return [
            f"+{commit.additions} lines",
            f"-{commit.deletions} lines",
            f"{len(commit.files_changed)} files changed",
        ]

    def _extract_lessons_from_commit(self, commit: CommitInfo) -> List[str]:
        """Extract lessons learned from a commit."""
        lessons = []

        if "bug" in commit.message.lower():
            lessons.append("Bug fixes indicate areas that need attention")

        if "refactor" in commit.message.lower():
            lessons.append("Refactorings show code quality improvements")

        if "performance" in commit.message.lower():
            lessons.append("Performance improvements show optimization efforts")

        if commit.deletions > commit.additions:
            lessons.append("Simplification: removed more than added")

        return lessons

    def _extract_lessons(self, commits: List[CommitInfo]) -> List[str]:
        """Extract overall lessons from commit history."""
        lessons = []

        # Count types of commits
        bug_fixes = len([c for c in commits if "bug" in c.message.lower()])
        refactors = len([c for c in commits if "refactor" in c.message.lower()])
        features = len([c for c in commits if "feat" in c.message.lower()])

        if bug_fixes > refactors:
            lessons.append("Focus on bug fixes - consider preventive measures")

        if refactors > 0:
            lessons.append("Regular refactoring shows commitment to code quality")

        if features > 0:
            lessons.append("Steady feature development indicates active project")

        # Commit frequency
        if commits:
            lessons.append(f"Project has {len(commits)} commits in recent period")

        return lessons


# Singleton instance
_analyzer_instance: Optional[GitAnalyzer] = None


def get_git_analyzer(repo_path: str = ".") -> GitAnalyzer:
    """Get or create git analyzer instance."""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = GitAnalyzer(repo_path)
    return _analyzer_instance
