"""
CONSOLIDATE Tool - Extract patterns from episodic events via consolidation

This tool is discoverable via filesystem and directly executable.
Agents can import and call this function directly.

Usage:
    from athena.tools.consolidation.consolidate import consolidate
    report = consolidate(strategy='quality', days_back=7)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from athena.manager import UnifiedMemoryManager


def consolidate(strategy: str = 'balanced', days_back: int = 7):
    """
    Extract patterns from episodic events (sleep-like consolidation)

    Parameters:
        strategy: Consolidation strategy - one of: balanced, speed, quality
        days_back: Number of days of events to consolidate (default: 7)

    Returns:
        ConsolidationReport - Extracted patterns with quality metrics

    Example:
        >>> report = consolidate(strategy='quality', days_back=14)
        >>> print(f"Extracted {len(report.patterns)} patterns")

    Raises:
        ValueError: If strategy is invalid
        RuntimeError: If consolidation process fails
    """
    valid_strategies = ['balanced', 'speed', 'quality']
    if strategy not in valid_strategies:
        raise ValueError(f"Invalid strategy: {strategy}. Must be one of {valid_strategies}")

    if not isinstance(days_back, int) or days_back <= 0:
        raise ValueError(f"days_back must be positive integer, got {days_back}")

    try:
        manager = UnifiedMemoryManager()
        report = manager.consolidate(strategy=strategy, days_back=days_back)
        return report
    except Exception as e:
        raise RuntimeError(f"Consolidation failed: {str(e)}") from e

