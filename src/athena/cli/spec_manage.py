#!/usr/bin/env python3
"""CLI tool for managing specifications in spec-driven development.

Usage:
    athena-spec-manage <command> [OPTIONS]

Commands:
    list            List specifications
    create          Create a new specification
    update          Update an existing specification
    delete          Delete a specification
    sync            Sync specifications from filesystem
    validate        Validate a specification
    diff            Compare two specification versions
    show            Show specification details

Examples:
    # List all specifications
    athena-spec-manage list

    # Create OpenAPI spec
    athena-spec-manage create --name "User API" --type openapi --file specs/user-api.yaml

    # Sync from filesystem
    athena-spec-manage sync --project-id 1

    # Validate spec
    athena-spec-manage validate --spec-id 5

    # Show spec details
    athena-spec-manage show --spec-id 5
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

from athena.core.database import get_database
from athena.architecture.spec_store import SpecificationStore
from athena.architecture.models import Specification, SpecType, SpecStatus


def cmd_list(args):
    """List specifications."""
    db = get_database()
    store = SpecificationStore(db)

    # Parse filters
    spec_type = SpecType(args.type) if args.type else None
    status = SpecStatus(args.status) if args.status else None

    specs = store.list_by_project(
        project_id=args.project_id,
        spec_type=spec_type,
        status=status,
        limit=args.limit
    )

    if args.json:
        output = [
            {
                "id": s.id,
                "name": s.name,
                "type": s.spec_type.value,
                "version": s.version,
                "status": s.status.value,
                "file_path": s.file_path,
                "created_at": s.created_at.isoformat(),
            }
            for s in specs
        ]
        print(json.dumps(output, indent=2))
    else:
        print(f"\n📋 Specifications (Project {args.project_id})")
        print("=" * 80)
        for spec in specs:
            status_emoji = {
                "draft": "📝",
                "active": "✅",
                "deprecated": "⚠️",
                "superseded": "🔄",
            }
            emoji = status_emoji.get(spec.status.value, "📄")
            print(f"\n{emoji} [{spec.id}] {spec.name} (v{spec.version})")
            print(f"   Type: {spec.spec_type.value}")
            print(f"   Status: {spec.status.value}")
            if spec.file_path:
                print(f"   File: {spec.file_path}")
            print(f"   Created: {spec.created_at.strftime('%Y-%m-%d %H:%M')}")

        print(f"\nTotal: {len(specs)} specifications")


def cmd_create(args):
    """Create a new specification."""
    db = get_database()
    store = SpecificationStore(db)

    # Read content from file or stdin
    if args.content_file:
        content = Path(args.content_file).read_text()
    elif args.content:
        content = args.content
    else:
        print("Reading content from stdin (press Ctrl+D when done):")
        content = sys.stdin.read()

    # Detect type from file extension if not specified
    spec_type = SpecType(args.type) if args.type else None
    if not spec_type and args.file_path:
        spec_type = store._detect_spec_type(Path(args.file_path))
    if not spec_type:
        spec_type = SpecType.MARKDOWN  # Default

    # Create specification
    spec = Specification(
        project_id=args.project_id,
        name=args.name,
        spec_type=spec_type,
        version=args.version,
        status=SpecStatus.DRAFT if args.draft else SpecStatus.ACTIVE,
        content=content,
        file_path=args.file_path,
        description=args.description,
        author=args.author,
        tags=args.tags.split(",") if args.tags else [],
    )

    spec_id = store.create(spec, write_to_file=not args.no_write_file)

    print(f"✅ Created specification {spec_id}: {spec.name} v{spec.version}")
    if spec.file_path and not args.no_write_file:
        print(f"   Wrote to: specs/{spec.file_path}")


def cmd_update(args):
    """Update an existing specification."""
    db = get_database()
    store = SpecificationStore(db)

    # Get existing spec
    spec = store.get(args.spec_id)
    if not spec:
        print(f"❌ Specification {args.spec_id} not found")
        sys.exit(1)

    # Update fields
    if args.name:
        spec.name = args.name
    if args.version:
        spec.version = args.version
    if args.status:
        spec.status = SpecStatus(args.status)
    if args.description:
        spec.description = args.description
    if args.content_file:
        spec.content = Path(args.content_file).read_text()
    if args.file_path:
        spec.file_path = args.file_path
    if args.tags:
        spec.tags = args.tags.split(",")

    store.update(spec, write_to_file=not args.no_write_file)

    print(f"✅ Updated specification {spec.id}: {spec.name} v{spec.version}")


def cmd_delete(args):
    """Delete a specification."""
    db = get_database()
    store = SpecificationStore(db)

    spec = store.get(args.spec_id)
    if not spec:
        print(f"❌ Specification {args.spec_id} not found")
        sys.exit(1)

    # Confirm deletion
    if not args.yes:
        response = input(f"Delete '{spec.name}' (v{spec.version})? [y/N]: ")
        if response.lower() != 'y':
            print("Cancelled")
            sys.exit(0)

    store.delete(args.spec_id, delete_file=args.delete_file)

    print(f"✅ Deleted specification {spec.id}: {spec.name}")
    if args.delete_file:
        print("   (file deleted from filesystem)")


def cmd_sync(args):
    """Sync specifications from filesystem."""
    db = get_database()
    store = SpecificationStore(db)

    print(f"🔄 Syncing specifications from {store.specs_dir}...")
    stats = store.sync_from_filesystem(project_id=args.project_id)

    print(f"\n✅ Sync complete:")
    print(f"   Created: {stats['created']}")
    print(f"   Updated: {stats['updated']}")
    print(f"   Skipped: {stats['skipped']}")


def cmd_show(args):
    """Show specification details."""
    db = get_database()
    store = SpecificationStore(db)

    spec = store.get(args.spec_id)
    if not spec:
        print(f"❌ Specification {args.spec_id} not found")
        sys.exit(1)

    if args.json:
        output = {
            "id": spec.id,
            "project_id": spec.project_id,
            "name": spec.name,
            "type": spec.spec_type.value,
            "version": spec.version,
            "status": spec.status.value,
            "file_path": spec.file_path,
            "description": spec.description,
            "related_adr_ids": spec.related_adr_ids,
            "implements_constraint_ids": spec.implements_constraint_ids,
            "uses_pattern_ids": spec.uses_pattern_ids,
            "validation_status": spec.validation_status,
            "validated_at": spec.validated_at.isoformat() if spec.validated_at else None,
            "tags": spec.tags,
            "author": spec.author,
            "created_at": spec.created_at.isoformat(),
            "updated_at": spec.updated_at.isoformat(),
            "content": spec.content if args.show_content else "<truncated>",
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"\n📄 Specification Details")
        print("=" * 80)
        print(f"ID: {spec.id}")
        print(f"Name: {spec.name}")
        print(f"Type: {spec.spec_type.value}")
        print(f"Version: {spec.version}")
        print(f"Status: {spec.status.value}")
        print(f"File: {spec.file_path or '(no file)'}")
        print(f"\nDescription:")
        print(f"  {spec.description or '(no description)'}")

        if spec.related_adr_ids:
            print(f"\nRelated ADRs: {', '.join(map(str, spec.related_adr_ids))}")
        if spec.implements_constraint_ids:
            print(f"Implements Constraints: {', '.join(map(str, spec.implements_constraint_ids))}")
        if spec.uses_pattern_ids:
            print(f"Uses Patterns: {', '.join(spec.uses_pattern_ids)}")

        if spec.validation_status:
            print(f"\nValidation Status: {spec.validation_status}")
            if spec.validated_at:
                print(f"Validated At: {spec.validated_at.strftime('%Y-%m-%d %H:%M')}")
            if spec.validation_errors:
                print(f"Errors: {len(spec.validation_errors)}")

        print(f"\nTags: {', '.join(spec.tags) if spec.tags else '(none)'}")
        print(f"Author: {spec.author or '(unknown)'}")
        print(f"Created: {spec.created_at.strftime('%Y-%m-%d %H:%M')}")
        print(f"Updated: {spec.updated_at.strftime('%Y-%m-%d %H:%M')}")

        if args.show_content:
            print(f"\n--- Content ({len(spec.content)} chars) ---")
            print(spec.content)


def cmd_validate(args):
    """Validate a specification."""
    db = get_database()
    store = SpecificationStore(db)

    spec = store.get(args.spec_id)
    if not spec:
        print(f"❌ Specification {args.spec_id} not found")
        sys.exit(1)

    print(f"🔍 Validating {spec.name} (v{spec.version})...")
    print(f"   Type: {spec.spec_type.value}")
    print()

    # Perform validation
    try:
        result = store.validate(args.spec_id, update_db=not args.no_update_db)

        # Print results
        if result.is_valid:
            if result.warnings:
                print(f"✅ Validation passed with {len(result.warnings)} warning(s)")
            else:
                print("✅ Validation passed - specification is valid!")
        else:
            print(f"❌ Validation failed with {len(result.errors)} error(s)")

        if result.validator_used and result.validator_used != "none":
            print(f"   Validator: {result.validator_used}")
        print()

        # Print errors
        if result.errors:
            print("❌ Errors:")
            for i, error in enumerate(result.errors, 1):
                print(f"  {i}. {error}")
            print()

        # Print warnings
        if result.warnings:
            print("⚠️  Warnings:")
            for i, warning in enumerate(result.warnings, 1):
                print(f"  {i}. {warning}")
            print()

        # Print validation metadata
        print(f"Validated at: {result.validated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Status: {result.status}")

        # Exit with error code if validation failed
        if not result.is_valid:
            sys.exit(1)

    except Exception as e:
        print(f"❌ Error during validation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def cmd_diff(args):
    """Compare two specification versions."""
    db = get_database()
    store = SpecificationStore(db)

    try:
        # Perform diff
        if args.compare_with_previous:
            # Compare with previous version
            result = store.diff_with_previous_version(args.spec_id)
            if not result:
                print(f"❌ No previous version found for specification {args.spec_id}")
                sys.exit(1)
        else:
            # Compare two specific specs
            if not args.new_spec_id:
                print("❌ Error: --new-spec-id is required (or use --compare-with-previous)")
                sys.exit(1)
            result = store.diff(args.spec_id, args.new_spec_id)

        # Print header
        print(f"\n📊 Specification Diff")
        print("=" * 80)
        print(f"Old: [{result.old_spec.id}] {result.old_spec.name} v{result.old_spec.version}")
        print(f"New: [{result.new_spec.id}] {result.new_spec.name} v{result.new_spec.version}")
        print()

        # Print summary
        summary = result.summary
        print(f"📈 Summary:")
        print(f"   Total changes: {summary['total_changes']}")
        print(f"   Breaking: {summary['breaking_changes']}")
        print(f"   Non-breaking: {summary['non_breaking_changes']}")
        print(f"   Added: {summary['added']}")
        print(f"   Removed: {summary['removed']}")
        print(f"   Modified: {summary['modified']}")
        print()

        # Show breaking changes warning
        if result.has_breaking_changes:
            print("⚠️  WARNING: This update contains BREAKING CHANGES!")
            print()

        # Print changes by severity
        if result.breaking_changes:
            print("💥 Breaking Changes:")
            for change in result.breaking_changes:
                icon = {
                    "added": "➕",
                    "removed": "➖",
                    "modified": "✏️",
                }.get(change.change_type.value, "•")
                print(f"   {icon} {change.path}")
                print(f"      {change.description}")
            print()

        if result.non_breaking_changes and not args.breaking_only:
            print("✨ Non-Breaking Changes:")
            for change in result.non_breaking_changes:
                icon = {
                    "added": "➕",
                    "removed": "➖",
                    "modified": "✏️",
                }.get(change.change_type.value, "•")
                print(f"   {icon} {change.path}")
                print(f"      {change.description}")
            print()

        if not result.changes:
            print("✅ No changes detected between versions")

        # Exit with error code if there are breaking changes and strict mode
        if args.strict and result.has_breaking_changes:
            print("❌ Exiting with error due to breaking changes (--strict mode)")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Error during diff: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Manage specifications for spec-driven development",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # List command
    list_parser = subparsers.add_parser("list", help="List specifications")
    list_parser.add_argument("--project-id", type=int, default=1, help="Project ID")
    list_parser.add_argument("--type", choices=[t.value for t in SpecType], help="Filter by type")
    list_parser.add_argument("--status", choices=[s.value for s in SpecStatus], help="Filter by status")
    list_parser.add_argument("--limit", type=int, default=100, help="Maximum results")
    list_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new specification")
    create_parser.add_argument("--project-id", type=int, default=1, help="Project ID")
    create_parser.add_argument("--name", required=True, help="Specification name")
    create_parser.add_argument("--type", choices=[t.value for t in SpecType], help="Spec type (auto-detected from file if not provided)")
    create_parser.add_argument("--version", default="1.0.0", help="Version (default: 1.0.0)")
    create_parser.add_argument("--file-path", help="Relative path in specs/ directory")
    create_parser.add_argument("--content", help="Specification content (or use --content-file or stdin)")
    create_parser.add_argument("--content-file", help="Read content from file")
    create_parser.add_argument("--description", help="Description")
    create_parser.add_argument("--author", help="Author name")
    create_parser.add_argument("--tags", help="Comma-separated tags")
    create_parser.add_argument("--draft", action="store_true", help="Mark as draft (default: active)")
    create_parser.add_argument("--no-write-file", action="store_true", help="Don't write to filesystem")

    # Update command
    update_parser = subparsers.add_parser("update", help="Update an existing specification")
    update_parser.add_argument("--spec-id", type=int, required=True, help="Specification ID")
    update_parser.add_argument("--name", help="New name")
    update_parser.add_argument("--version", help="New version")
    update_parser.add_argument("--status", choices=[s.value for s in SpecStatus], help="New status")
    update_parser.add_argument("--description", help="New description")
    update_parser.add_argument("--content-file", help="Read new content from file")
    update_parser.add_argument("--file-path", help="New file path")
    update_parser.add_argument("--tags", help="Comma-separated tags")
    update_parser.add_argument("--no-write-file", action="store_true", help="Don't write to filesystem")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a specification")
    delete_parser.add_argument("--spec-id", type=int, required=True, help="Specification ID")
    delete_parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")
    delete_parser.add_argument("--delete-file", action="store_true", help="Also delete file from filesystem")

    # Sync command
    sync_parser = subparsers.add_parser("sync", help="Sync specifications from filesystem")
    sync_parser.add_argument("--project-id", type=int, default=1, help="Project ID")

    # Show command
    show_parser = subparsers.add_parser("show", help="Show specification details")
    show_parser.add_argument("--spec-id", type=int, required=True, help="Specification ID")
    show_parser.add_argument("--show-content", action="store_true", help="Show full content")
    show_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate a specification")
    validate_parser.add_argument("--spec-id", type=int, required=True, help="Specification ID")
    validate_parser.add_argument("--no-update-db", action="store_true", help="Don't update validation status in database")

    # Diff command
    diff_parser = subparsers.add_parser("diff", help="Compare two specification versions")
    diff_parser.add_argument("--spec-id", type=int, required=True, help="Old specification ID")
    diff_parser.add_argument("--new-spec-id", type=int, help="New specification ID (required unless --compare-with-previous)")
    diff_parser.add_argument("--compare-with-previous", action="store_true", help="Compare with previous version of same spec")
    diff_parser.add_argument("--breaking-only", action="store_true", help="Show only breaking changes")
    diff_parser.add_argument("--strict", action="store_true", help="Exit with error code if breaking changes detected")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Route to command handler
    commands = {
        "list": cmd_list,
        "create": cmd_create,
        "update": cmd_update,
        "delete": cmd_delete,
        "sync": cmd_sync,
        "show": cmd_show,
        "validate": cmd_validate,
        "diff": cmd_diff,
    }

    try:
        commands[args.command](args)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
