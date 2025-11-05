"""Git-aware temporal models for version control integration.

Enables linking code changes to commits, tracking regression history,
and analyzing author patterns in the temporal chain.

Based on temporal chain architecture extended with VCS metadata.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class GitChangeType(str, Enum):
    """Types of git changes tracked."""

    ADDED = "added"  # New file
    MODIFIED = "modified"  # File changed
    DELETED = "deleted"  # File removed
    RENAMED = "renamed"  # File renamed
    COPIED = "copied"  # File copied
    MERGED = "merged"  # Merge conflict resolved


class GitEventType(str, Enum):
    """Types of git-aware events."""

    COMMIT = "commit"  # New commit
    BRANCH_CREATE = "branch_create"  # New branch
    BRANCH_DELETE = "branch_delete"  # Branch deleted
    MERGE = "merge"  # Branch merge
    REBASE = "rebase"  # Rebase operation
    CHERRY_PICK = "cherry_pick"  # Cherry-pick operation
    STASH = "stash"  # Stash created/applied
    RESET = "reset"  # Hard/soft reset


class RegressionType(str, Enum):
    """Types of regressions that can be tracked."""

    BUG_INTRODUCTION = "bug_introduction"  # Commit that introduced bug
    PERFORMANCE_DEGRADATION = "perf_degradation"  # Performance regression
    FEATURE_BREAKAGE = "feature_breakage"  # Feature stopped working
    TEST_FAILURE = "test_failure"  # Test started failing
    MEMORY_LEAK = "memory_leak"  # Memory leak introduced
    SECURITY_ISSUE = "security_issue"  # Security vulnerability


@dataclass
class GitMetadata:
    """Git-level metadata for an event."""

    commit_hash: str  # SHA1 or abbreviated hash
    commit_message: str  # Full commit message
    author: str  # Author name/email
    author_email: Optional[str] = None
    committer: Optional[str] = None  # Committer name (may differ from author)
    committer_email: Optional[str] = None
    committed_timestamp: datetime = field(default_factory=datetime.now)
    branch: str = "main"  # Branch name
    files_changed: int = 0  # Number of files in commit
    insertions: int = 0  # Lines added
    deletions: int = 0  # Lines deleted
    parents: list[str] = field(default_factory=list)  # Parent commit hashes

    def __post_init__(self):
        """Validate git metadata."""
        if not self.commit_hash:
            raise ValueError("commit_hash is required")
        if not self.commit_message:
            raise ValueError("commit_message is required")
        if not self.author:
            raise ValueError("author is required")
        if self.files_changed < 0:
            raise ValueError("files_changed must be >= 0")
        if self.insertions < 0:
            raise ValueError("insertions must be >= 0")
        if self.deletions < 0:
            raise ValueError("deletions must be >= 0")


@dataclass
class GitFileChange:
    """A single file change in a commit."""

    file_path: str  # Absolute path to file
    change_type: GitChangeType  # Type of change (added, modified, etc)
    old_path: Optional[str] = None  # Original path if renamed
    insertions: int = 0  # Lines added
    deletions: int = 0  # Lines deleted
    patch: Optional[str] = None  # Diff content (optional, can be large)
    hunks: int = 0  # Number of diff hunks

    def __post_init__(self):
        """Validate file change."""
        if not self.file_path:
            raise ValueError("file_path is required")
        if self.insertions < 0:
            raise ValueError("insertions must be >= 0")
        if self.deletions < 0:
            raise ValueError("deletions must be >= 0")


@dataclass
class GitCommitEvent:
    """A git commit with associated metadata and file changes."""

    git_metadata: GitMetadata  # Core git info
    event_id: Optional[int] = None  # Reference to episodic event
    file_changes: list[GitFileChange] = field(default_factory=list)
    related_issues: list[str] = field(default_factory=list)  # Issue IDs mentioned
    code_review_url: Optional[str] = None  # PR/MR link if available
    is_merge_commit: bool = False  # Whether this is a merge commit
    is_release: bool = False  # Whether this is a release commit

    def __post_init__(self):
        """Validate commit event."""
        if not self.git_metadata:
            raise ValueError("git_metadata is required")

    def total_changes(self) -> int:
        """Total lines changed in commit."""
        return self.git_metadata.insertions + self.git_metadata.deletions


@dataclass
class RegressionAnalysis:
    """Analysis linking a regression to its introducing commit."""

    regression_type: RegressionType
    regression_description: str
    introducing_commit: str  # Commit hash that introduced regression
    discovered_commit: str  # Commit hash where regression was discovered
    discovered_event_id: Optional[int] = None  # Episodic event ID
    fix_commit: Optional[str] = None  # Commit hash that fixed it (if known)
    affected_files: list[str] = field(default_factory=list)  # Files involved
    affected_symbols: list[str] = field(default_factory=list)  # Functions/classes affected
    root_cause_analysis: Optional[str] = None  # Analysis of why it happened
    impact_estimate: float = 0.5  # 0-1, estimated impact severity
    confidence: float = 0.5  # 0-1, confidence in the link
    bisect_verified: bool = False  # Whether git bisect confirmed it

    def __post_init__(self):
        """Validate regression analysis."""
        if not self.introducing_commit:
            raise ValueError("introducing_commit is required")
        if not self.discovered_commit:
            raise ValueError("discovered_commit is required")
        if not (0.0 <= self.impact_estimate <= 1.0):
            raise ValueError(f"impact_estimate must be [0-1], got {self.impact_estimate}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be [0-1], got {self.confidence}")


@dataclass
class AuthorMetrics:
    """Metrics about an author's contribution patterns."""

    author: str
    email: Optional[str] = None
    commits_count: int = 0
    files_changed_total: int = 0
    insertions_total: int = 0
    deletions_total: int = 0
    merge_commits: int = 0
    regressions_introduced: int = 0  # Count of regressions they introduced
    regressions_fixed: int = 0  # Count of regressions they fixed
    avg_commit_size: float = 0.0  # Average lines per commit
    specialization: Optional[str] = None  # Domain they focus on (e.g., "auth", "api")
    last_commit_timestamp: Optional[datetime] = None
    most_frequent_file_patterns: list[str] = field(default_factory=list)  # Files they often touch

    def __post_init__(self):
        """Validate author metrics."""
        if not self.author:
            raise ValueError("author is required")


@dataclass
class GitTemporalRelation:
    """Temporal relationship between git commits."""

    from_commit: str  # Source commit hash
    to_commit: str  # Target commit hash
    relation_type: str  # 'introduces_regression', 'fixes_regression', 'depends_on', 'precedes'
    strength: float  # 0-1, confidence in relation
    distance_commits: int = 0  # Number of commits between them
    time_delta_seconds: int = 0  # Time between commits
    file_overlap: float = 0.0  # 0-1, fraction of overlapping files
    inferred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate git temporal relation."""
        valid_types = {
            "introduces_regression",
            "fixes_regression",
            "depends_on",
            "precedes",
            "cherry_picked_from",
        }
        if self.relation_type not in valid_types:
            raise ValueError(f"Invalid relation_type: {self.relation_type}")
        if not (0.0 <= self.strength <= 1.0):
            raise ValueError(f"strength must be [0-1], got {self.strength}")
        if self.distance_commits < 0:
            raise ValueError("distance_commits must be >= 0")
        if self.file_overlap < 0.0 or self.file_overlap > 1.0:
            raise ValueError(f"file_overlap must be [0-1], got {self.file_overlap}")


@dataclass
class BranchMetrics:
    """Metrics about a git branch."""

    branch_name: str
    is_main: bool = False
    is_protected: bool = False
    created_timestamp: datetime = field(default_factory=datetime.now)
    last_commit_timestamp: Optional[datetime] = None
    commits_ahead_of_main: int = 0
    commits_behind_main: int = 0
    merge_commits_on_branch: int = 0
    open_regressions: int = 0  # Regressions on this branch

    def __post_init__(self):
        """Validate branch metrics."""
        if not self.branch_name:
            raise ValueError("branch_name is required")
