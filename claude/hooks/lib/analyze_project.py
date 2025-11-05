#!/usr/bin/env python3
"""Execute project analysis and store results.

This script is called by /analyze-project slash command.
"""

import sys
import json
import argparse
from pathlib import Path

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze project structure and build memory"
    )
    parser.add_argument(
        "project_path",
        nargs="?",
        default=".",
        help="Path to project root (default: current directory)"
    )
    parser.add_argument(
        "--output",
        choices=["json", "summary"],
        default="summary",
        help="Output format"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress messages"
    )

    args = parser.parse_args()

    try:
        # Add Athena to path - check multiple locations for flexibility
        athena_path = Path.home() / ".work" / "athena" / "src"
        if not athena_path.exists():
            # Fallback to relative path for backwards compatibility
            athena_path = Path(__file__).parent.parent.parent.parent / "athena" / "src"
        if not athena_path.exists():
            # Last fallback: old location
            athena_path = Path(__file__).parent.parent.parent.parent / "memory-mcp" / "src"

        sys.path.insert(0, str(athena_path))

        from athena.analysis import ProjectAnalyzer, ProjectAnalysisMemoryStorage
        from athena.core.database import Database

        project_path = Path(args.project_path).resolve()

        if not args.quiet:
            print(f"Analyzing project: {project_path}", file=sys.stderr)

        # Perform analysis
        analyzer = ProjectAnalyzer(str(project_path))
        analysis = analyzer.analyze()

        if not args.quiet:
            print(f"✓ Scan complete: {analysis.total_files} files, "
                  f"{analysis.total_lines} lines", file=sys.stderr)

        # Store in memory
        db_path = Path.home() / ".athena" / "memory.db"
        db = Database(str(db_path))
        storage = ProjectAnalysisMemoryStorage(db)
        storage_result = storage.store_analysis(analysis)

        if not args.quiet:
            print(f"✓ Stored in memory: {storage_result['stored_items']} items",
                  file=sys.stderr)

        # Output results
        if args.output == "json":
            result = {
                "status": "success",
                "project": analysis.project_name,
                "files": analysis.total_files,
                "lines": analysis.total_lines,
                "languages": analysis.languages,
                "components": len(analysis.components),
                "patterns": len(analysis.patterns),
                "metrics": {
                    "complexity": round(analysis.avg_complexity, 2),
                    "test_ratio": round(analysis.test_file_ratio, 2),
                    "documentation": round(analysis.documentation_score, 2),
                },
                "insights": analysis.insights,
                "recommendations": analysis.recommendations,
                "storage": storage_result,
            }
            print(json.dumps(result))
        else:
            # Summary format
            print(f"\n{'='*60}")
            print(f"PROJECT ANALYSIS: {analysis.project_name}")
            print(f"{'='*60}")
            print(f"\nPath: {analysis.project_path}")
            print(f"\n📊 STATISTICS")
            print(f"  Files: {analysis.total_files}")
            print(f"  Lines: {analysis.total_lines:,}")
            print(f"  Languages: {', '.join(f'{k}({v})' for k, v in analysis.languages.items())}")
            print(f"\n🏗️  STRUCTURE")
            print(f"  Components: {len(analysis.components)}")
            for comp in analysis.components[:5]:
                print(f"    • {comp.name}: {len(comp.files)} files, "
                      f"complexity={comp.complexity:.2f}, "
                      f"test_coverage={comp.test_coverage:.0%}")

            print(f"\n📈 QUALITY METRICS")
            print(f"  Complexity: {analysis.avg_complexity:.2f}/1.0", end="")
            if analysis.avg_complexity > 0.7:
                print(" ⚠️  High")
            elif analysis.avg_complexity < 0.3:
                print(" ✓ Low")
            else:
                print(" ○ Moderate")

            print(f"  Test Coverage: {analysis.test_file_ratio:.0%}", end="")
            if analysis.test_file_ratio > 0.3:
                print(" ✓")
            elif analysis.test_file_ratio > 0:
                print(" ○")
            else:
                print(" ⚠️  None")

            print(f"  Documentation: {analysis.documentation_score:.0%}")

            print(f"\n💡 INSIGHTS")
            for insight in analysis.insights:
                print(f"  • {insight}")

            print(f"\n📋 RECOMMENDATIONS")
            for rec in analysis.recommendations:
                print(f"  • {rec}")

            print(f"\n💾 MEMORY STORAGE")
            print(f"  Items stored: {storage_result['stored_items']}")
            print(f"  Components: {len(storage_result['entities'])}")
            print(f"  Relations: {len(storage_result['relations'])}")

            print(f"\n{'='*60}")
            print("✓ Analysis complete and stored in memory system")
            print("  Use /memory-query to search findings")
            print("  Use /plan build to create plans with project knowledge")

        return 0

    except Exception as e:
        error_result = {
            "status": "error",
            "error": str(e),
        }
        print(json.dumps(error_result))
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
