#!/usr/bin/env python3
"""
Hook System Library - Phases 1-8

Provides unified access to all hook modules for sequential, parallel, and optimized execution.

Global access: All modules in ~/.claude/hooks/lib are available

Usage:
    # Direct imports (works from anywhere after sourcing hook_lib.env)
    from async_hook_orchestrator import AsyncHookOrchestrator
    from critical_path_analyzer import CriticalPathAnalyzer
    from hook_cache import HookResultCache
    from background_executor import BackgroundExecutor

    # Or from Python code that adds lib to path:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path.home() / ".claude" / "hooks" / "lib"))
    from async_hook_orchestrator import AsyncHookOrchestrator
"""

import sys
from pathlib import Path

# Ensure this directory is in Python path for imports
_lib_path = Path(__file__).parent
if str(_lib_path) not in sys.path:
    sys.path.insert(0, str(_lib_path))

# Phase 6: Parallel Hook Execution
try:
    from async_hook_orchestrator import (
        AsyncHookOrchestrator,
        ExecutionGroup,
        HookStatus,
        HookExecution,
    )
    PHASE_6_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    PHASE_6_AVAILABLE = False
    AsyncHookOrchestrator = None
    ExecutionGroup = None
    HookStatus = None
    HookExecution = None

# Phase 7: Critical Path Analysis
try:
    from critical_path_analyzer import (
        CriticalPathAnalyzer,
        HookMetrics,
        CriticalPathResult,
    )
    PHASE_7_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    PHASE_7_AVAILABLE = False
    CriticalPathAnalyzer = None
    HookMetrics = None
    CriticalPathResult = None

# Phase 8: Performance Optimization
try:
    from hook_cache import (
        HookResultCache,
        CacheEntry,
        CacheStats,
        compute_input_hash,
    )
    PHASE_8A_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    PHASE_8A_AVAILABLE = False
    HookResultCache = None
    CacheEntry = None
    CacheStats = None
    compute_input_hash = None

try:
    from background_executor import (
        BackgroundExecutor,
        SmartBackgroundScheduler,
        BackgroundTask,
        BackgroundTaskStatus,
    )
    PHASE_8B_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    PHASE_8B_AVAILABLE = False
    BackgroundExecutor = None
    SmartBackgroundScheduler = None
    BackgroundTask = None
    BackgroundTaskStatus = None

# Version
__version__ = "1.0"
__author__ = "Claude Code"
__status__ = "Production Ready"

# Public API
__all__ = [
    # Phase 6
    "AsyncHookOrchestrator",
    "ExecutionGroup",
    "HookStatus",
    "HookExecution",
    # Phase 7
    "CriticalPathAnalyzer",
    "HookMetrics",
    "CriticalPathResult",
    # Phase 8a
    "HookResultCache",
    "CacheEntry",
    "CacheStats",
    "compute_input_hash",
    # Phase 8b
    "BackgroundExecutor",
    "SmartBackgroundScheduler",
    "BackgroundTask",
    "BackgroundTaskStatus",
    # Status
    "PHASE_6_AVAILABLE",
    "PHASE_7_AVAILABLE",
    "PHASE_8A_AVAILABLE",
    "PHASE_8B_AVAILABLE",
]


def get_availability_report():
    """Get report of which phases are available"""
    return {
        "phase_6_parallel_execution": PHASE_6_AVAILABLE,
        "phase_7_critical_path": PHASE_7_AVAILABLE,
        "phase_8a_caching": PHASE_8A_AVAILABLE,
        "phase_8b_background": PHASE_8B_AVAILABLE,
        "all_phases_available": all([
            PHASE_6_AVAILABLE,
            PHASE_7_AVAILABLE,
            PHASE_8A_AVAILABLE,
            PHASE_8B_AVAILABLE,
        ]),
    }


if __name__ == "__main__":
    import json
    report = get_availability_report()
    print(json.dumps(report, indent=2))
