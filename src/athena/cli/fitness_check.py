#!/usr/bin/env python3
"""CLI tool for running architecture fitness checks.

Usage:
    athena-fitness-check [OPTIONS]

    Options:
        --project-root PATH     Project root directory (default: current dir)
        --severity LEVEL        Only run functions of this severity (error/warning/info)
        --category CAT          Only run functions of this category
        --fail-on-critical      Exit with code 1 if any ERROR severity fails
        --json                  Output results as JSON
        --verbose               Show detailed output

Examples:
    # Run all checks
    athena-fitness-check

    # Run only critical checks (for CI)
    athena-fitness-check --severity error --fail-on-critical

    # Run only layering checks
    athena-fitness-check --category layering

    # Get JSON output
    athena-fitness-check --json > results.json
"""

import argparse
import json
import sys
from pathlib import Path

# Import fitness tests to register them
import tests.architecture.test_fitness_functions  # noqa: F401
from athena.architecture.fitness import (
    Category,
    FitnessChecker,
    Severity,
)


def main():
    parser = argparse.ArgumentParser(
        description="Run architecture fitness checks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Project root directory (default: current directory)",
    )

    parser.add_argument(
        "--severity",
        type=str,
        choices=["error", "warning", "info"],
        help="Only run functions of this severity",
    )

    parser.add_argument(
        "--category",
        type=str,
        choices=[c.value for c in Category],
        help="Only run functions of this category",
    )

    parser.add_argument(
        "--fail-on-critical",
        action="store_true",
        help="Exit with code 1 if any ERROR severity fails (for CI/hooks)",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed output",
    )

    args = parser.parse_args()

    # Convert string to enum
    severity_filter = None
    if args.severity:
        severity_filter = Severity(args.severity)

    category_filter = None
    if args.category:
        category_filter = Category(args.category)

    # Run checks
    checker = FitnessChecker(args.project_root)
    results = checker.run_all(
        severity_filter=severity_filter,
        category_filter=category_filter,
    )

    # Output
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_human_readable(results, verbose=args.verbose)

    # Exit code
    if args.fail_on_critical and checker.check_should_block_commit(results):
        sys.exit(1)
    elif results["summary"]["failed"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


def print_human_readable(results: dict, verbose: bool = False):
    """Print results in human-readable format."""
    summary = results["summary"]

    # Header
    print("\n" + "=" * 70)
    print("🏗️  ARCHITECTURE FITNESS CHECK RESULTS")
    print("=" * 70)
    print(f"Project: {results['project_root']}")
    print(f"Timestamp: {results['timestamp']}")
    print()

    # Summary
    print(f"📊 Summary:")
    print(f"   Total functions: {summary['total_functions']}")
    print(f"   Passed: ✅ {summary['passed']}")
    print(f"   Failed: ❌ {summary['failed']}")
    print(f"   Total violations: {summary['total_violations']}")
    print()

    # Results by category
    if verbose or summary["failed"] > 0:
        print("📋 Results by Function:")
        print()

        for result in results["results"]:
            status = "✅" if result["passed"] else "❌"
            severity_emoji = {
                "error": "🚫",
                "warning": "⚠️",
                "info": "ℹ️",
            }[result["severity"]]

            print(f"{status} {result['name']}")
            print(f"   Category: {result['category']} | Severity: {severity_emoji} {result['severity']}")
            print(f"   {result['message']}")

            if result["violations"] and (verbose or not result["passed"]):
                print(f"   Violations ({len(result['violations'])}):")
                for i, violation in enumerate(result["violations"][:10], 1):  # Show max 10
                    print(f"     {i}. {violation['file']}:{violation['line']}")
                    print(f"        {violation['description']}")
                    if violation.get("suggested_fix"):
                        print(f"        → Fix: {violation['suggested_fix']}")

                if len(result["violations"]) > 10:
                    print(f"     ... and {len(result['violations']) - 10} more")

            print()

    # Footer
    print("=" * 70)

    if summary["failed"] == 0:
        print("✅ All architecture fitness checks passed!")
    else:
        print(f"❌ {summary['failed']} fitness check(s) failed")
        print()
        print("💡 Tips:")
        print("   • Fix ERROR severity violations to unblock commit/build")
        print("   • Address WARNING severity violations to improve architecture")
        print("   • Run with --verbose to see all violations")

    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
