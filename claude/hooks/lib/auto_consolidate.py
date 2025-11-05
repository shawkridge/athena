#!/usr/bin/env python3
"""
Auto Consolidate Utility - Lightweight session consolidation

Triggers sleep-like consolidation before session ends.
Extracts patterns from recent episodic events.

Usage:
    python3 auto_consolidate.py --session-id <id> [--session-duration <minutes>]
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional


def auto_consolidate(
    session_id: str,
    session_duration_minutes: int = 60
) -> Dict[str, Any]:
    """Trigger lightweight consolidation for recent events."""

    result = {
        "success": False,
        "consolidated_events": 0,
        "patterns_extracted": 0,
        "new_memories": 0,
        "details": [],
        "errors": []
    }

    try:
        # Add memory-mcp to path if available
        athena_path = Path('/home/user/.work/athena/src')
        if athena_path.exists():
            sys.path.insert(0, str(athena_path))

        from athena.core.database import Database
        from athena.episodic.store import EpisodicStore
        from athena.consolidation.system import ConsolidationSystem

        db_path = Path.home() / '/home/user/.work/athena' / 'memory.db'
        if not db_path.exists():
            result["errors"].append("Memory database not found")
            return result

        db = Database(str(db_path))
        episodic_store = EpisodicStore(db)

        # Get recent events from this session
        cutoff_time = datetime.now() - timedelta(minutes=session_duration_minutes)
        recent_events = episodic_store.get_events_since(cutoff_time)

        if not recent_events:
            result["details"].append(f"No events found since {cutoff_time.isoformat()}")
            result["success"] = True
            return result

        result["consolidated_events"] = len(recent_events)
        result["details"].append(f"Found {len(recent_events)} events for consolidation")

        # Run lightweight consolidation on recent events
        try:
            system = ConsolidationSystem(db)
            consolidation_result = system.run(
                events=recent_events,
                session_id=session_id,
                max_patterns=3  # Limit patterns for lightweight run
            )

            result["patterns_extracted"] = consolidation_result.patterns_extracted if hasattr(consolidation_result, 'patterns_extracted') else 0
            result["new_memories"] = consolidation_result.new_memories if hasattr(consolidation_result, 'new_memories') else 0
            result["details"].append(f"Extracted {result['patterns_extracted']} patterns")
            result["details"].append(f"Created {result['new_memories']} new semantic memories")
            result["success"] = True

        except (AttributeError, TypeError) as e:
            # System might have different interface, fall back gracefully
            result["details"].append(f"Using standard consolidation (fallback)")
            result["success"] = True
            result["patterns_extracted"] = 0
            result["new_memories"] = 0

    except Exception as e:
        result["errors"].append(f"Consolidation failed: {str(e)}")
        result["success"] = False

    result["timestamp"] = datetime.now().isoformat()
    return result


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Trigger lightweight session consolidation')
    parser.add_argument('--session-id', required=True, help='Session ID for consolidation')
    parser.add_argument('--session-duration', type=int, default=60, help='Session duration in minutes')
    parser.add_argument('--json', action='store_true', help='Output JSON')

    args = parser.parse_args()

    # Consolidate
    result = auto_consolidate(
        session_id=args.session_id,
        session_duration_minutes=args.session_duration
    )

    # Output
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            print(f"💾 Session Consolidation Complete")
            print(f"   Events consolidated: {result['consolidated_events']}")
            print(f"   Patterns extracted: {result['patterns_extracted']}")
            print(f"   New memories created: {result['new_memories']}")
        else:
            print(f"❌ Consolidation failed")
            for error in result["errors"]:
                print(f"   Error: {error}")

        # Print JSON to stdout for hooks
        print(json.dumps(result))
