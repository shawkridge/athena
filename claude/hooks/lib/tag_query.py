#!/usr/bin/env python3
"""
Tag Query Utility - Auto-tag user prompts and discover related memories

When user submits a prompt, automatically:
1. Tag the query with semantic metadata
2. Discover related memories
3. Record as episodic event

Usage:
    python3 tag_query.py --query <query> --session-id <id> [--cwd <path>]
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional


def extract_tags(query: str) -> List[str]:
    """Extract semantic tags from user query."""
    tags = []

    # Domain detection
    domains = {
        "bug": ["debug", "error", "fix", "fail"],
        "feature": ["add", "implement", "create", "new"],
        "refactor": ["refactor", "clean", "reorgan", "simplif"],
        "test": ["test", "test", "coverage", "assert"],
        "documentation": ["doc", "comment", "readme", "guide"],
        "performance": ["perf", "optim", "speed", "fast"],
        "security": ["secure", "auth", "encrypt", "token"],
    }

    query_lower = query.lower()
    for domain, keywords in domains.items():
        if any(kw in query_lower for kw in keywords):
            tags.append(domain)

    # Priority detection
    if any(word in query_lower for word in ["urgent", "critical", "asap", "immediately"]):
        tags.append("urgent")
    if any(word in query_lower for word in ["research", "explore", "investigate"]):
        tags.append("research")
    if any(word in query_lower for word in ["question", "help", "confused", "unclear"]):
        tags.append("question")

    return tags if tags else ["general"]


def discover_related_memories(
    query: str,
    tags: List[str]
) -> Dict[str, Any]:
    """Discover related memories for the query."""

    discovered = {
        "count": 0,
        "memory_ids": [],
        "queries_suggested": []
    }

    try:
        # Add memory-mcp to path if available
        athena_path = Path('/home/user/.work/athena/src')
        if athena_path.exists():
            sys.path.insert(0, str(athena_path))

        from athena.core.database import Database
        from athena.memory.store import MemoryStore

        db_path = Path.home() / '/home/user/.work/athena' / 'memory.db'
        if not db_path.exists():
            discovered["note"] = "Memory database not found"
            return discovered

        db = Database(str(db_path))
        memory_store = MemoryStore(db)

        # Search by query
        results = memory_store.search(query)
        discovered["count"] = len(results)
        discovered["memory_ids"] = [r.get("id") for r in results[:5]]  # Top 5

        # Suggest follow-up queries based on tags
        tag_to_query = {
            "bug": "/memory-query 'recent debugging sessions'",
            "feature": "/memory-query 'feature implementation patterns'",
            "test": "/memory-query 'testing best practices'",
            "documentation": "/memory-query 'documentation standards'",
            "research": "/memory-query 'research findings and insights'",
        }

        for tag in tags:
            if tag in tag_to_query:
                discovered["queries_suggested"].append(tag_to_query[tag])

    except Exception as e:
        discovered["discovery_note"] = f"Memory discovery: {str(e)}"

    return discovered


def tag_query(
    query: str,
    session_id: str,
    cwd: Optional[str] = None
) -> Dict[str, Any]:
    """Tag user query and discover related memories."""

    result = {
        "success": True,
        "query": query,
        "session_id": session_id,
        "tags": [],
        "discovered_memories": {},
        "metadata": {},
        "errors": []
    }

    try:
        # Extract tags from query
        tags = extract_tags(query)
        result["tags"] = tags

        # Discover related memories
        discovered = discover_related_memories(query, tags)
        result["discovered_memories"] = discovered

        # Record metadata
        result["metadata"] = {
            "query_length": len(query),
            "tag_count": len(tags),
            "memories_found": discovered["count"],
            "timestamp": datetime.now().isoformat(),
            "cwd": cwd or "unknown"
        }

        result["success"] = True

    except Exception as e:
        result["errors"].append(str(e))
        result["success"] = False

    return result


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Tag user query and discover related memories')
    parser.add_argument('--query', required=True, help='User query/prompt')
    parser.add_argument('--session-id', required=True, help='Session ID')
    parser.add_argument('--cwd', help='Current working directory (optional)')
    parser.add_argument('--json', action='store_true', help='Output JSON')

    args = parser.parse_args()

    # Tag and discover
    result = tag_query(
        query=args.query,
        session_id=args.session_id,
        cwd=args.cwd
    )

    # Output
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"🏷️  Query Tagged: {', '.join(result['tags'])}")
        print(f"   Memories discovered: {result['discovered_memories']['count']}")
        if result['discovered_memories']['queries_suggested']:
            print(f"   Related queries: {len(result['discovered_memories']['queries_suggested'])}")

        # Print JSON for hooks
        print(json.dumps(result))
