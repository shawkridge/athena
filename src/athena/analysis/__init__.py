"""Project and library analysis module for building memory about codebases and dependencies."""

from .project_analyzer import (
    ProjectAnalyzer,
    ProjectAnalysis,
    ComponentInfo,
    PatternFound,
    FileMetrics,
)
from .semantic_storage import ProjectAnalysisMemoryStorage
from .library_analyzer import (
    LibraryDependencyAnalyzer,
    LibraryAnalysis,
    DependencyVersion,
    LibraryCapabilities,
    VulnerabilitySeverity,
    get_analyzer,
)

__all__ = [
    "ProjectAnalyzer",
    "ProjectAnalysis",
    "ProjectAnalysisMemoryStorage",
    "ComponentInfo",
    "PatternFound",
    "FileMetrics",
    "LibraryDependencyAnalyzer",
    "LibraryAnalysis",
    "DependencyVersion",
    "LibraryCapabilities",
    "VulnerabilitySeverity",
    "get_analyzer",
]
