#!/usr/bin/env python
"""Script to help migrate tools from handlers.py to modular structure."""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from athena.tools.migration import ToolExtractor, ToolMigrator, BackwardCompatibilityLayer


def main():
    """Run tool migration."""
    # Paths
    project_root = Path(__file__).parent.parent
    handlers_file = project_root / "src" / "athena" / "mcp" / "handlers.py"
    tools_base_dir = project_root / "src" / "athena" / "tools"
    mcp_dir = project_root / "src" / "athena" / "mcp"

    print("=" * 80)
    print("MCP Tool Migration Script")
    print("=" * 80)

    # Check if handlers.py exists
    if not handlers_file.exists():
        print(f"ERROR: handlers.py not found at {handlers_file}")
        return 1

    # Initialize extractor and migrator
    print(f"\n1. Analyzing handlers.py at {handlers_file}")
    extractor = ToolExtractor(handlers_file)
    tools = extractor.find_tools()
    categories = extractor.get_tool_categories()

    print(f"   Found {len(tools)} tools in {len(categories)} categories:")
    for category, tool_list in sorted(categories.items()):
        print(f"   - {category}: {len(tool_list)} tools")
        for tool in sorted(tool_list)[:3]:  # Show first 3
            print(f"     * {tool}")
        if len(tool_list) > 3:
            print(f"     * ... and {len(tool_list) - 3} more")

    # Show migration status
    print(f"\n2. Migration Status")
    migrator = ToolMigrator(handlers_file, tools_base_dir)
    status = migrator.get_migration_status()
    print(f"   Total tools to migrate: {status['total_tools_in_handlers']}")
    print(f"   Already migrated: {status['migrated_tools']}")
    print(f"   Remaining: {status['remaining_tools']}")
    print(f"   Progress: {status['migration_percentage']:.1f}%")

    # Interactive migration menu
    print(f"\n3. Migration Options")
    print("   a) Migrate specific tools")
    print("   b) Migrate all tools")
    print("   c) Migrate by category")
    print("   d) Show tool details")
    print("   e) Exit")

    choice = input("\nSelect option (a-e): ").strip().lower()

    if choice == "a":
        # Migrate specific tools
        tools_to_migrate = input("Enter tool names (comma-separated): ").split(",")
        tools_to_migrate = [t.strip() for t in tools_to_migrate]
        migrated = migrator.migrate_tools(tools_to_migrate)
        print(f"\nMigrated {len(migrated)} tools:")
        for tool, path in migrated.items():
            print(f"  ✓ {tool} -> {path.relative_to(project_root)}")

    elif choice == "b":
        # Migrate all tools
        print("Migrating all tools...")
        migrated = migrator.migrate_tools()
        print(f"\nMigrated {len(migrated)} tools:")
        for tool, path in sorted(migrated.items()):
            print(f"  ✓ {tool} -> {path.relative_to(project_root)}")

    elif choice == "c":
        # Migrate by category
        print("Available categories:", ", ".join(sorted(categories.keys())))
        category = input("Select category: ").strip().lower()
        if category in categories:
            tools_to_migrate = categories[category]
            migrated = migrator.migrate_tools(tools_to_migrate)
            print(f"\nMigrated {len(migrated)} tools from '{category}':")
            for tool in sorted(tools_to_migrate):
                print(f"  ✓ {tool}")
        else:
            print(f"Category '{category}' not found")

    elif choice == "d":
        # Show tool details
        tool_name = input("Enter tool name: ").strip()
        if tool_name in tools:
            tool_info = tools[tool_name]
            print(f"\nTool: {tool_name}")
            print(f"  Docstring: {tool_info['docstring'][:100]}...")
            print(f"  Parameters: {', '.join(tool_info['args'])}")
            print(f"  Lines: {tool_info['lineno']}-{tool_info['lineno_end']}")

            # Show extracted source
            source = extractor.extract_tool_method(tool_name)
            if source:
                print(f"\n  Source (first 500 chars):")
                print("  " + "\n  ".join(source[:500].split("\n")))
        else:
            print(f"Tool '{tool_name}' not found")

    elif choice == "e":
        print("Exiting...")
        return 0

    # Final status
    print(f"\n4. Updated Migration Status")
    status = migrator.get_migration_status()
    print(f"   Total tools: {status['total_tools_in_handlers']}")
    print(f"   Migrated: {status['migrated_tools']}")
    print(f"   Remaining: {status['remaining_tools']}")
    print(f"   Progress: {status['migration_percentage']:.1f}%")

    print("\n" + "=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
