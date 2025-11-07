#!/usr/bin/env python3
"""
Example: Find common architectural and design patterns in code.

This script helps identify:
- Singleton pattern
- Factory pattern
- Observer pattern
- Repository pattern
- Service pattern

Usage:
    python find_patterns.py /path/to/repo [language]
"""

import sys
from pathlib import Path

from athena.code_search.tree_sitter_search import TreeSitterCodeSearch


class PatternFinder:
    """Find design patterns in code."""

    def __init__(self, repo_path, language="python"):
        self.search = TreeSitterCodeSearch(repo_path, language=language)
        self.search.build_index()
        self.language = language

    def find_singletons(self):
        """Find potential singleton classes/objects."""
        print("\n🔍 Singleton Pattern Detection\n")
        print("-" * 60)

        # Look for getInstance, instance, sharedInstance methods
        results = self.search.search("getInstance instance shared", limit=30)

        singletons = {}
        for result in results:
            if result.unit.type in ("function", "method"):
                # Try to find the class containing this method
                class_name = result.unit.file_path.split("/")[-1].replace(".py", "").replace(".js", "")
                if "instance" in result.unit.name.lower():
                    singletons[class_name] = result.unit.name

        if singletons:
            print(f"✅ Found {len(singletons)} potential singletons:\n")
            for class_name, method_name in sorted(singletons.items())[:10]:
                print(f"  - {class_name}.{method_name}()")
        else:
            print("❌ No singletons found")

    def find_factories(self):
        """Find factory pattern implementations."""
        print("\n🏭 Factory Pattern Detection\n")
        print("-" * 60)

        # Look for Factory, Builder, create methods
        results = self.search.search("factory builder create", limit=50)

        factories = {}
        for result in results:
            if result.unit.type == "class" and ("Factory" in result.unit.name or "Builder" in result.unit.name):
                factories[result.unit.name] = result.unit.file_path

        if factories:
            print(f"✅ Found {len(factories)} factory/builder classes:\n")
            for name, file_path in sorted(factories.items())[:10]:
                print(f"  - {name} ({Path(file_path).name})")
        else:
            print("❌ No factory patterns found")

    def find_repositories(self):
        """Find repository pattern implementations."""
        print("\n📚 Repository Pattern Detection\n")
        print("-" * 60)

        # Look for Repository classes
        results = self.search.search_by_type("class", limit=100)

        repositories = {}
        for result in results:
            if "Repository" in result.unit.name or "Dao" in result.unit.name:
                # Check for database operation methods
                if result.unit.dependencies:
                    repositories[result.unit.name] = result.unit.dependencies

        if repositories:
            print(f"✅ Found {len(repositories)} repository classes:\n")
            for name, dependencies in sorted(repositories.items())[:10]:
                print(f"  - {name}")
                if dependencies:
                    deps_list = list(dependencies)[:3]
                    print(f"    Methods: {deps_list}")
        else:
            print("❌ No repository patterns found")

    def find_services(self):
        """Find service layer implementations."""
        print("\n🔧 Service Pattern Detection\n")
        print("-" * 60)

        # Look for Service classes
        results = self.search.search_by_type("class", limit=100)

        services = {}
        for result in results:
            if "Service" in result.unit.name or "Manager" in result.unit.name:
                services[result.unit.name] = result.unit.file_path

        if services:
            print(f"✅ Found {len(services)} service classes:\n")
            for name, file_path in sorted(services.items())[:10]:
                print(f"  - {name} ({Path(file_path).name})")
        else:
            print("❌ No service patterns found")

    def find_observers(self):
        """Find observer pattern implementations."""
        print("\n👁️  Observer Pattern Detection\n")
        print("-" * 60)

        # Look for subscribe, notify, publish methods
        results = self.search.search("subscribe notify publish", limit=50)

        observers = {}
        for result in results:
            if result.unit.type == "class":
                if result.unit.name not in observers:
                    observers[result.unit.name] = []
                observers[result.unit.name].append(result.unit.file_path)

        if observers:
            print(f"✅ Found {len(observers)} potential observer classes:\n")
            for name, files in sorted(observers.items())[:10]:
                print(f"  - {name} ({Path(files[0]).name})")
        else:
            print("❌ No observer patterns found")

    def analyze_all(self):
        """Run all pattern analyses."""
        stats = self.search.get_code_statistics()
        print(f"\n{'='*60}")
        print(f"Code Analysis Report")
        print(f"{'='*60}\n")
        print(f"Language: {self.language}")
        print(f"Files: {stats.total_files}")
        print(f"Code Units: {stats.total_units}\n")

        self.find_singletons()
        self.find_factories()
        self.find_repositories()
        self.find_services()
        self.find_observers()

        print(f"\n{'='*60}")
        print("✅ Pattern analysis complete")
        print(f"{'='*60}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python find_patterns.py <repo_path> [language]")
        print("\nSupported languages: python, javascript, java, go")
        print("\nExample:")
        print("  python find_patterns.py ./my_project python")
        print("  python find_patterns.py ./my_project javascript")
        sys.exit(1)

    repo_path = sys.argv[1]
    language = sys.argv[2] if len(sys.argv) > 2 else "python"

    if not Path(repo_path).exists():
        print(f"Error: Repository path '{repo_path}' does not exist")
        sys.exit(1)

    print(f"🔍 Design Pattern Finder")
    print(f"📂 Repository: {repo_path}")
    print(f"🔤 Language: {language}")

    try:
        finder = PatternFinder(repo_path, language)
        finder.analyze_all()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
