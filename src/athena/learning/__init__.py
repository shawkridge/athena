"""Strategies 1, 3, 5: Learning systems - Extract knowledge from git, errors, and code."""

from .git_analyzer import (
    GitAnalyzer,
    CommitInfo,
    ArchitecturalDecision,
    PatternEvolution,
    get_git_analyzer,
)
from .decision_extractor import (
    DecisionExtractor,
    Decision,
    DecisionLibrary,
)
from .error_diagnostician import (
    ErrorDiagnostician,
    DiagnosedError,
    ErrorPattern,
    ErrorFrequency,
)
from .pattern_detector import (
    PatternDetector,
    CodePattern,
    DuplicateGroup,
)

__all__ = [
    # Strategy 5: Git History
    "GitAnalyzer",
    "CommitInfo",
    "ArchitecturalDecision",
    "PatternEvolution",
    "get_git_analyzer",
    "DecisionExtractor",
    "Decision",
    "DecisionLibrary",
    # Strategy 1: Error Diagnosis
    "ErrorDiagnostician",
    "DiagnosedError",
    "ErrorPattern",
    "ErrorFrequency",
    # Strategy 3: Pattern Detection
    "PatternDetector",
    "CodePattern",
    "DuplicateGroup",
]
