"""CLI module for Athena memory system.

Provides command-line interface for slash commands following Anthropic's
code-execution-with-MCP pattern:
- Discover operations
- Execute locally
- Return summaries (300 tokens max)
"""

from .commands import (
    MemorySearchCommand,
    PlanTaskCommand,
    ValidatePlanCommand,
    SessionStartCommand,
    ManageGoalCommand,
)

# Import CLI classes from cli.py module to support mcp handlers
# This resolves the naming conflict between cli.py (module) and cli/ (package)
try:
    import importlib.util
    from pathlib import Path

    cli_py_path = Path(__file__).parent.parent / "cli.py"
    spec = importlib.util.spec_from_file_location("_athena_cli_module", cli_py_path)

    if spec and spec.loader:
        cli_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli_module)

        # Export classes from cli.py
        ATHENAAnalyzer = cli_module.ATHENAAnalyzer
        AnalysisConfig = cli_module.AnalysisConfig
        AnalysisProfile = cli_module.AnalysisProfile
        OutputFormat = cli_module.OutputFormat
    else:
        raise ImportError("Could not load cli.py module")

except (ImportError, AttributeError, Exception) as e:
    # Create stubs if import fails
    class ATHENAAnalyzer:
        """Stub for when cli.py is unavailable."""
        def __init__(self, *args, **kwargs):
            raise NotImplementedError("ATHENAAnalyzer is not available")

    class AnalysisConfig:
        """Stub for when cli.py is unavailable."""
        pass

    class AnalysisProfile:
        """Stub for when cli.py is unavailable."""
        pass

    class OutputFormat:
        """Stub for when cli.py is unavailable."""
        pass

__all__ = [
    "MemorySearchCommand",
    "PlanTaskCommand",
    "ValidatePlanCommand",
    "SessionStartCommand",
    "ManageGoalCommand",
    "ATHENAAnalyzer",
    "AnalysisConfig",
    "AnalysisProfile",
    "OutputFormat",
]
