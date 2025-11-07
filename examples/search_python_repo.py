#!/usr/bin/env python3
"""
Example: Search a Python codebase for authentication functions.

Usage:
    python search_python_repo.py /path/to/python/repo "authenticate"
"""

import sys
from pathlib import Path

from athena.code_search.tree_sitter_search import TreeSitterCodeSearch


def main():
    if len(sys.argv) < 2:
        print("Usage: python search_python_repo.py <repo_path> [query]")
        print("\nExample:")
        print("  python search_python_repo.py ./my_project")
        print("  python search_python_repo.py ./my_project 'authenticate'")
        sys.exit(1)

    repo_path = sys.argv[1]
    query = sys.argv[2] if len(sys.argv) > 2 else "authenticate"

    if not Path(repo_path).exists():
        print(f"Error: Repository path '{repo_path}' does not exist")
        sys.exit(1)

    print(f"🔍 Searching Python repository: {repo_path}")
    print(f"📝 Query: '{query}'\n")

    # Initialize search engine
    search = TreeSitterCodeSearch(repo_path, language="python")

    # Build index
    print("📚 Building index...")
    search.build_index()

    # Get statistics
    stats = search.get_code_statistics()
    print(f"✅ Indexed {stats.total_files} files with {stats.total_units} code units\n")

    # Search
    print(f"🔎 Searching for '{query}'...\n")
    results = search.search(query, limit=20)

    if not results:
        print("❌ No results found")
        return

    print(f"✅ Found {len(results)} results:\n")
    print("-" * 80)

    for i, result in enumerate(results, 1):
        unit = result.unit
        print(f"{i}. {unit.name} ({unit.type})")
        print(f"   Location: {unit.file_path}:{unit.start_line}")
        print(f"   Score: {result.score:.2f}")

        if unit.signature:
            sig = unit.signature[:100]
            sig += "..." if len(unit.signature) > 100 else ""
            print(f"   Signature: {sig}")

        if unit.docstring:
            doc = unit.docstring[:100]
            doc += "..." if len(unit.docstring) > 100 else ""
            print(f"   Doc: {doc}")

        if unit.dependencies:
            deps = list(unit.dependencies)[:3]
            print(f"   Dependencies: {deps}")

        print()

    # Search by type
    print("\n" + "=" * 80)
    print("📂 Code Units by Type:\n")

    for unit_type in ["function", "class", "import"]:
        type_results = search.search_by_type(unit_type, limit=10)
        print(f"{unit_type.upper()}S ({len(type_results)} found):")
        for result in type_results[:5]:
            print(f"  - {result.unit.name} ({result.unit.file_path})")
        if len(type_results) > 5:
            print(f"  ... and {len(type_results) - 5} more")
        print()


if __name__ == "__main__":
    main()
