#!/usr/bin/env python3
"""CLI tool for architecture impact analysis.

Usage:
    athena-impact-analysis [COMMAND] [OPTIONS]

Commands:
    adr-change          Analyze impact of changing an ADR
    add-constraint      Analyze impact of adding a constraint
    pattern-change      Analyze impact of changing a pattern
    dependency-graph    Generate dependency graph
    blast-radius        Calculate blast radius for a component

Examples:
    # Analyze ADR change
    athena-impact-analysis adr-change --adr-id 12 --change "Switch to session auth"

    # Analyze new constraint
    athena-impact-analysis add-constraint --type performance --description "API < 200ms"

    # Generate dependency graph
    athena-impact-analysis dependency-graph --project-id 1 --output graph.json

    # Calculate blast radius
    athena-impact-analysis blast-radius --adr-id 12
"""

import argparse
import json
import sys
from pathlib import Path

from athena.architecture.impact_analyzer import (
    EffortEstimate,
    ImpactAnalyzer,
    RiskLevel,
)
from athena.core.database import get_database


def main():
    parser = argparse.ArgumentParser(
        description="Architecture impact analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # ADR change analysis
    adr_parser = subparsers.add_parser(
        "adr-change", help="Analyze impact of changing an ADR"
    )
    adr_parser.add_argument("--adr-id", type=int, required=True, help="ADR ID to analyze")
    adr_parser.add_argument(
        "--change", required=True, help="Description of proposed change"
    )
    adr_parser.add_argument("--project-id", type=int, help="Project ID (optional)")
    adr_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Constraint addition analysis
    constraint_parser = subparsers.add_parser(
        "add-constraint", help="Analyze impact of adding a constraint"
    )
    constraint_parser.add_argument(
        "--type", required=True, help="Constraint type (performance/security/etc)"
    )
    constraint_parser.add_argument(
        "--description", required=True, help="Constraint description"
    )
    constraint_parser.add_argument(
        "--criteria", default="", help="Validation criteria"
    )
    constraint_parser.add_argument(
        "--project-id", type=int, required=True, help="Project ID"
    )
    constraint_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Pattern change analysis
    pattern_parser = subparsers.add_parser(
        "pattern-change", help="Analyze impact of changing a pattern"
    )
    pattern_parser.add_argument("--pattern", required=True, help="Pattern name")
    pattern_parser.add_argument(
        "--change-type",
        required=True,
        choices=["adopt", "modify", "deprecate"],
        help="Type of change",
    )
    pattern_parser.add_argument(
        "--project-id", type=int, required=True, help="Project ID"
    )
    pattern_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Dependency graph
    graph_parser = subparsers.add_parser(
        "dependency-graph", help="Generate dependency graph"
    )
    graph_parser.add_argument(
        "--project-id", type=int, required=True, help="Project ID"
    )
    graph_parser.add_argument(
        "--output", type=Path, help="Output file (default: stdout)"
    )
    graph_parser.add_argument(
        "--format", choices=["json", "dot"], default="json", help="Output format"
    )

    # Blast radius
    blast_parser = subparsers.add_parser(
        "blast-radius", help="Calculate blast radius for a component"
    )
    blast_parser.add_argument("--adr-id", type=int, help="ADR ID")
    blast_parser.add_argument("--pattern", type=str, help="Pattern name")
    blast_parser.add_argument(
        "--project-id", type=int, required=True, help="Project ID"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Initialize analyzer
    db = get_database()
    analyzer = ImpactAnalyzer(db, Path.cwd())

    # Execute command
    if args.command == "adr-change":
        handle_adr_change(analyzer, args)
    elif args.command == "add-constraint":
        handle_constraint_addition(analyzer, args)
    elif args.command == "pattern-change":
        handle_pattern_change(analyzer, args)
    elif args.command == "dependency-graph":
        handle_dependency_graph(analyzer, args)
    elif args.command == "blast-radius":
        handle_blast_radius(analyzer, args)


def handle_adr_change(analyzer: ImpactAnalyzer, args):
    """Handle ADR change analysis command."""
    print(f"\n🔍 Analyzing impact of changing ADR-{args.adr_id}...")
    print(f"   Proposed change: {args.change}\n")

    impact = analyzer.analyze_adr_change(
        adr_id=args.adr_id,
        proposed_change=args.change,
        project_id=args.project_id,
    )

    if args.json:
        print(json.dumps(impact.to_dict(), indent=2))
        return

    # Human-readable output
    print("=" * 70)
    print("📊 IMPACT ANALYSIS RESULTS")
    print("=" * 70)
    print()

    # Risk and effort
    risk_emoji = {
        "low": "🟢",
        "medium": "🟡",
        "high": "🟠",
        "critical": "🔴",
    }
    print(f"Risk Level: {risk_emoji[impact.risk_level.value]} {impact.risk_level.value.upper()}")
    print(f"Estimated Effort: {impact.estimated_effort.value.replace('_', ' ').title()}")
    print(f"Blast Radius: {impact.blast_radius_score:.1%} of system")
    print(f"Reversibility: {impact.reversibility_score:.1%}")
    print(f"Breaking Changes: {'⚠️ YES' if impact.breaking_changes else '✅ NO'}")
    print()

    # Affected items
    if impact.affected_components:
        print(f"📦 Affected Components ({len(impact.affected_components)}):")
        for comp in impact.affected_components[:10]:
            print(f"   • {comp.name} ({comp.type.value})")
        if len(impact.affected_components) > 10:
            print(f"   ... and {len(impact.affected_components) - 10} more")
        print()

    if impact.affected_adrs:
        print(f"📋 Related ADRs ({len(impact.affected_adrs)}):")
        for adr_id in impact.affected_adrs:
            print(f"   • ADR-{adr_id}")
        print()

    # Warnings
    if impact.warnings:
        print("⚠️  Warnings:")
        for warning in impact.warnings:
            print(f"   • {warning}")
        print()

    # Recommendations
    if impact.recommendations:
        print("💡 Recommendations:")
        for rec in impact.recommendations:
            print(f"   • {rec}")
        print()

    print("=" * 70)


def handle_constraint_addition(analyzer: ImpactAnalyzer, args):
    """Handle constraint addition analysis command."""
    print(f"\n🔍 Analyzing impact of adding constraint...")
    print(f"   Type: {args.type}")
    print(f"   Description: {args.description}\n")

    impact = analyzer.analyze_constraint_addition(
        constraint_description=args.description,
        constraint_type=args.type,
        validation_criteria=args.criteria,
        project_id=args.project_id,
    )

    if args.json:
        print(json.dumps(impact.to_dict(), indent=2))
        return

    # Human-readable output
    print("=" * 70)
    print("📊 CONSTRAINT IMPACT ANALYSIS")
    print("=" * 70)
    print()

    print(f"Current Violations: {impact.current_violations}")
    print(f"Affected Files: {len(impact.affected_files)}")
    print(f"Estimated Fix Effort: {impact.estimated_fix_effort.value.replace('_', ' ').title()}")
    print(f"Breaking Changes: {'⚠️ YES' if impact.breaking_changes else '✅ NO'}")
    print()

    if impact.affected_files:
        print("📁 Affected Files:")
        for file in impact.affected_files[:10]:
            print(f"   • {file}")
        if len(impact.affected_files) > 10:
            print(f"   ... and {len(impact.affected_files) - 10} more")
        print()

    if impact.recommendations:
        print("💡 Recommendations:")
        for rec in impact.recommendations:
            print(f"   • {rec}")
        print()

    print("=" * 70)


def handle_pattern_change(analyzer: ImpactAnalyzer, args):
    """Handle pattern change analysis command."""
    print(f"\n🔍 Analyzing impact of {args.change_type} pattern: {args.pattern}...\n")

    impact = analyzer.analyze_pattern_change(
        pattern_name=args.pattern,
        change_type=args.change_type,
        project_id=args.project_id,
    )

    if args.json:
        print(json.dumps(impact.to_dict(), indent=2))
        return

    # Human-readable output
    print("=" * 70)
    print("📊 PATTERN IMPACT ANALYSIS")
    print("=" * 70)
    print()

    risk_emoji = {
        "low": "🟢",
        "medium": "🟡",
        "high": "🟠",
        "critical": "🔴",
    }
    print(f"Risk Level: {risk_emoji[impact.risk_level.value]} {impact.risk_level.value.upper()}")
    print(f"Estimated Effort: {impact.estimated_effort.value.replace('_', ' ').title()}")
    print()

    usage_count = impact.metadata.get("usage_count", 0)
    print(f"Current Usage: {usage_count} times")
    print()

    if impact.recommendations:
        print("💡 Recommendations:")
        for rec in impact.recommendations:
            print(f"   • {rec}")
        print()

    print("=" * 70)


def handle_dependency_graph(analyzer: ImpactAnalyzer, args):
    """Handle dependency graph generation command."""
    print(f"\n🔍 Building dependency graph for project {args.project_id}...\n")

    graph = analyzer.get_dependency_graph(args.project_id)

    if args.format == "json":
        graph_dict = graph.to_dict()
        output = json.dumps(graph_dict, indent=2)
    elif args.format == "dot":
        # Generate GraphViz DOT format
        output = "digraph architecture {\n"
        output += "  rankdir=LR;\n"
        output += "  node [shape=box];\n\n"

        for node in graph.nodes:
            label = node.name.replace('"', '\\"')
            output += f'  "{node}" [label="{label}"];\n'

        output += "\n"

        for edge in graph.edges:
            output += f'  "{edge.source}" -> "{edge.target}" [label="{edge.dependency_type}"];\n'

        output += "}\n"

    # Write output
    if args.output:
        args.output.write_text(output)
        print(f"✅ Dependency graph written to {args.output}")
    else:
        print(output)

    print(f"\n📊 Graph Statistics:")
    print(f"   Nodes: {len(graph.nodes)}")
    print(f"   Edges: {len(graph.edges)}")

    # Check for circular dependencies
    cycles = graph.find_circular_dependencies()
    if cycles:
        print(f"\n⚠️  Found {len(cycles)} circular dependencies:")
        for i, cycle in enumerate(cycles[:5], 1):
            cycle_str = " → ".join(c.name for c in cycle)
            print(f"   {i}. {cycle_str}")
    else:
        print(f"\n✅ No circular dependencies found")


def handle_blast_radius(analyzer: ImpactAnalyzer, args):
    """Handle blast radius calculation command."""
    graph = analyzer.get_dependency_graph(args.project_id)

    # Find component
    component = None
    if args.adr_id:
        for node in graph.nodes:
            if node.metadata.get("adr_id") == args.adr_id:
                component = node
                break
    elif args.pattern:
        for node in graph.nodes:
            if node.name == f"Pattern: {args.pattern}":
                component = node
                break

    if not component:
        print("❌ Component not found")
        sys.exit(1)

    blast_radius = graph.calculate_blast_radius(component)
    affected = graph.get_transitive_dependents(component)

    print(f"\n💥 Blast Radius Analysis: {component.name}")
    print("=" * 70)
    print(f"Blast Radius: {blast_radius:.1%} of system")
    print(f"Direct Dependents: {len(graph.get_dependents_of(component))}")
    print(f"Total Affected Components: {len(affected)}")
    print()

    if affected:
        print("📦 Affected Components:")
        for comp in list(affected)[:10]:
            print(f"   • {comp.name}")
        if len(affected) > 10:
            print(f"   ... and {len(affected) - 10} more")


if __name__ == "__main__":
    main()
