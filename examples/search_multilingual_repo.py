#!/usr/bin/env python3
"""
Example: Search multiple language codebases in a polyglot project.

This script searches for common patterns across Python, JavaScript, Java, and Go
to understand a microservices architecture.

Usage:
    python search_multilingual_repo.py /path/to/services
"""

import sys
from pathlib import Path

from athena.code_search.tree_sitter_search import TreeSitterCodeSearch


def analyze_language(language_name, repo_path, language_code, search_term):
    """Analyze a single language repository."""

    service_path = repo_path / language_name.lower()

    if not service_path.exists():
        print(f"⚠️  {language_name} service not found at {service_path}")
        return None

    print(f"\n{'='*80}")
    print(f"Analyzing {language_name} Service")
    print(f"{'='*80}\n")

    search = TreeSitterCodeSearch(str(service_path), language=language_code)
    search.build_index()

    stats = search.get_code_statistics()
    print(f"📊 Statistics:")
    print(f"  Files: {stats.total_files}")
    print(f"  Total Units: {stats.total_units}")

    # Count by type
    units_by_type = {}
    for unit in stats.units:
        unit_type = unit.type
        units_by_type[unit_type] = units_by_type.get(unit_type, 0) + 1

    print(f"  By Type:")
    for unit_type, count in sorted(units_by_type.items()):
        print(f"    - {unit_type}: {count}")

    # Search for common patterns
    print(f"\n🔍 Searching for: '{search_term}'")
    results = search.search(search_term, limit=10)

    if results:
        print(f"  Found {len(results)} matches:")
        for result in results[:5]:
            print(f"    - {result.unit.name} (score: {result.score:.2f})")
            if len(results) > 5:
                print(f"    ... and {len(results) - 5} more")
    else:
        print("  No matches found")

    return search


def main():
    if len(sys.argv) < 2:
        print("Usage: python search_multilingual_repo.py <services_base_path>")
        print("\nExample:")
        print("  python search_multilingual_repo.py ./services")
        print("\nExpected directory structure:")
        print("  services/")
        print("    python/   (Python backend)")
        print("    javascript/ (JavaScript/Node services)")
        print("    java/      (Java microservices)")
        print("    go/        (Go utilities)")
        sys.exit(1)

    base_path = Path(sys.argv[1])

    if not base_path.exists():
        print(f"Error: Path '{base_path}' does not exist")
        sys.exit(1)

    print("🏗️  Polyglot Microservices Architecture Analysis")
    print(f"📂 Base Path: {base_path}\n")

    # Define services
    services = [
        ("Python", "python"),
        ("JavaScript", "javascript"),
        ("Java", "java"),
        ("Go", "go"),
    ]

    search_engines = {}

    # Analyze each service
    for display_name, lang_code in services:
        search = analyze_language(display_name, base_path, lang_code, "authenticate")
        if search:
            search_engines[display_name] = search

    # Cross-service analysis
    print(f"\n{'='*80}")
    print("Cross-Service Analysis")
    print(f"{'='*80}\n")

    # Find authentication patterns
    print("🔐 Authentication Implementations Across Services:\n")
    for service_name, search in search_engines.items():
        results = search.search("authenticate auth", limit=5)
        if results:
            print(f"{service_name}:")
            for result in results[:3]:
                print(f"  - {result.unit.name} in {Path(result.unit.file_path).name}")

    # Find error handling
    print("\n❌ Error Handling Across Services:\n")
    for service_name, search in search_engines.items():
        results = search.search("error exception", limit=5)
        error_count = len(results)
        print(f"{service_name}: {error_count} error handling operations")

    # Find API operations
    print("\n🌐 API Operations by Service:\n")
    patterns = [
        ("Python", "route endpoint"),
        ("JavaScript", "router controller"),
        ("Java", "mapping rest"),
        ("Go", "handler http"),
    ]

    for service_name, pattern in patterns:
        if service_name in search_engines:
            search = search_engines[service_name]
            results = search.search(pattern, limit=20)
            print(f"{service_name}: {len(results)} API operations found")

    # Summary statistics
    print(f"\n{'='*80}")
    print("Summary Statistics")
    print(f"{'='*80}\n")

    total_files = 0
    total_units = 0

    for service_name, search in search_engines.items():
        stats = search.get_code_statistics()
        total_files += stats.total_files
        total_units += stats.total_units

    print(f"Total Services: {len(search_engines)}")
    print(f"Total Files Analyzed: {total_files}")
    print(f"Total Code Units: {total_units}")
    print(f"Languages: {', '.join([s[0] for s in services if s[0] in search_engines])}")


if __name__ == "__main__":
    main()
