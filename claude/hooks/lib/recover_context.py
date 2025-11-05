#!/usr/bin/env python3
"""
Context Recovery Helper
=======================
Detects if user is asking for context recovery and synthesizes recovered context
from episodic memory. Used by user-prompt-submit hook.

Recovery Trigger Patterns:
  - "What were we working on?"
  - "Let's continue"
  - "Where were we?"
  - "What's next?"
  - "Resume work"
  - "Where did we leave off?"
  - And 10+ more...

Output: JSON with recovery_detected, recovered_context (if found)
"""

import json
import sys
import argparse
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Import Memory MCP
try:
    sys.path.insert(0, '/home/user/.work/athena/src')
    from athena.conversation.auto_recovery import AutoContextRecovery
    from athena.core.database import Database
except ImportError as e:
    logger.warning(f"Could not import Memory MCP: {e}")


def check_recovery_request(user_query: str) -> bool:
    """Check if user query matches recovery trigger patterns."""
    recovery_patterns = [
        r"what\s+were\s+we\s+(?:working\s+on|doing)",
        r"let['\s]+s\s+continue",
        r"where\s+were\s+we",
        r"what['\s]+s\s+next",
        r"resume\s+work",
        r"where\s+did\s+we\s+leave\s+off",
        r"pick\s+up\s+where\s+we\s+left\s+off",
        r"restore\s+context",
        r"recover\s+context",
        r"what\s+(?:was\s+)?i\s+(?:was\s+)?doing",
        r"remind\s+me",
        r"what\s+do\s+we\s+have\s+going",
        r"where\s+are\s+we\s+(?:at|in)",
        r"bring\s+me\s+back\s+up\s+to\s+speed",
        r"fill\s+me\s+in",
    ]

    import re
    query_lower = user_query.lower()

    for pattern in recovery_patterns:
        if re.search(pattern, query_lower):
            return True

    return False


def synthesize_recovery_context(db_path: str, project_id: int = 1) -> dict:
    """Synthesize recovery context from episodic memory."""
    try:
        db = Database(db_path)
        recovery = AutoContextRecovery(db, project_id)

        # Get recovered context
        context = recovery.auto_recover_context()

        if context:
            return {
                "status": "success",
                "recovered": True,
                "context": context,
            }
        else:
            return {
                "status": "no_context",
                "recovered": False,
                "context": None,
            }
    except Exception as e:
        logger.error(f"Error synthesizing recovery context: {e}")
        return {
            "status": "error",
            "recovered": False,
            "context": None,
            "error": str(e),
        }


def format_recovery_output(context: dict) -> str:
    """Format recovered context as readable banner."""
    if not context:
        return ""

    lines = []
    lines.append("═" * 60)
    lines.append("🔄 CONTEXT RECOVERY")
    lines.append("═" * 60)

    if context.get("task"):
        lines.append(f"📋 Task: {context['task']}")

    if context.get("phase"):
        lines.append(f"⏱️  Phase: {context['phase']}")

    if context.get("recent_files"):
        lines.append(f"📁 Recent files: {', '.join(context['recent_files'][:3])}")

    if context.get("conversation_summary"):
        lines.append(f"💬 Last discussion: {context['conversation_summary'][:100]}...")

    if context.get("time_delta"):
        lines.append(f"⏳ Time since: {context['time_delta']}")

    lines.append("═" * 60)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Recover user context from memory")
    parser.add_argument("--query", required=True, help="User query to analyze")
    parser.add_argument("--db-path", default=str(Path.home() / '.athena/memory.db'),
                        help="Path to memory database")
    parser.add_argument("--project-id", type=int, default=1, help="Project ID")
    parser.add_argument("--json", action="store_true", help="Output JSON format")

    args = parser.parse_args()

    # Check if this is a recovery request
    is_recovery = check_recovery_request(args.query)

    result = {
        "recovery_detected": is_recovery,
        "recovered_context": None,
        "recovery_banner": None,
    }

    if is_recovery:
        # Synthesize recovery context
        recovery_result = synthesize_recovery_context(args.db_path, args.project_id)

        if recovery_result["status"] == "success":
            result["recovered_context"] = recovery_result["context"]
            result["recovery_banner"] = format_recovery_output(recovery_result["context"])

    if args.json:
        print(json.dumps(result))
    else:
        print(json.dumps(result, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
