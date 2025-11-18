#!/usr/bin/env python3
"""CLI tool for managing generated documentation.

Usage:
    athena-doc-manage <command> [OPTIONS]

Commands:
    list            List documents
    create          Create a new document
    generate        Generate document from specification (template-based)
    generate-ai     Generate document using AI from specification
    update          Update an existing document
    delete          Delete a document
    show            Show document details
    templates       List available templates

Examples:
    # List all documents
    athena-doc-manage list

    # Generate API docs from spec (template-based)
    athena-doc-manage generate --spec-id 5 --type api_doc --output docs/api.md

    # Generate TDD using AI
    athena-doc-manage generate-ai --spec-id 5 --type tdd --preview

    # Create manual document
    athena-doc-manage create --name "Deployment Guide" --type deployment --file ops/deploy.md

    # List available templates
    athena-doc-manage templates --category api

    # Show document details
    athena-doc-manage show --doc-id 10
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

from athena.core.database import get_database
from athena.architecture.doc_store import DocumentStore
from athena.architecture.spec_store import SpecificationStore
from athena.architecture.models import Document, DocumentType, DocumentStatus
from athena.architecture.templates import TemplateManager, TemplateContext
from athena.architecture.generators import AIDocGenerator, ContextAssembler


def cmd_list(args):
    """List documents."""
    db = get_database()
    store = DocumentStore(db)

    # Parse filters
    doc_type = DocumentType(args.type) if args.type else None
    status = DocumentStatus(args.status) if args.status else None

    docs = store.list_by_project(
        project_id=args.project_id,
        doc_type=doc_type,
        status=status,
        limit=args.limit
    )

    if args.json:
        output = [
            {
                "id": d.id,
                "name": d.name,
                "type": d.doc_type.value,
                "version": d.version,
                "status": d.status.value,
                "file_path": d.file_path,
                "generated_by": d.generated_by,
                "created_at": d.created_at.isoformat(),
            }
            for d in docs
        ]
        print(json.dumps(output, indent=2))
    else:
        print(f"\n📚 Documents (Project {args.project_id})")
        print("=" * 80)
        for doc in docs:
            status_emoji = {
                "draft": "📝",
                "review": "👀",
                "approved": "✅",
                "published": "📖",
                "deprecated": "⚠️",
            }
            emoji = status_emoji.get(doc.status.value, "📄")

            gen_badge = ""
            if doc.generated_by == "ai":
                gen_badge = " 🤖"
            elif doc.generated_by == "template":
                gen_badge = " 📋"

            print(f"\n{emoji} [{doc.id}] {doc.name} (v{doc.version}){gen_badge}")
            print(f"   Type: {doc.doc_type.value}")
            print(f"   Status: {doc.status.value}")
            if doc.file_path:
                print(f"   File: {doc.file_path}")
            if doc.based_on_spec_ids:
                print(f"   Based on specs: {doc.based_on_spec_ids}")
            print(f"   Created: {doc.created_at.strftime('%Y-%m-%d %H:%M')}")

        print(f"\nTotal: {len(docs)} documents")
        print(f"\n🤖 AI-generated | 📋 Template-based | 📝 Manual\n")


def cmd_create(args):
    """Create a new document."""
    db = get_database()
    store = DocumentStore(db)

    # Read content from file
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"❌ File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        content = file_path.read_text()
        relative_path = args.file
    else:
        content = args.content or "# " + args.name
        relative_path = None

    # Create document
    doc = Document(
        project_id=args.project_id,
        name=args.name,
        doc_type=DocumentType(args.type),
        version=args.version,
        status=DocumentStatus(args.status),
        content=content,
        file_path=relative_path,
        description=args.description,
        author=args.author,
    )

    doc_id = store.create(doc, write_to_file=not args.no_write_file)

    print(f"\n✅ Created document {doc_id}: {doc.name}")
    print(f"   Type: {doc.doc_type.value}")
    print(f"   Version: {doc.version}")
    if doc.file_path:
        print(f"   Saved to: {doc.file_path}")


def cmd_generate(args):
    """Generate document from specification."""
    db = get_database()
    doc_store = DocumentStore(db)
    spec_store = SpecificationStore(db)

    # Load specification
    spec = spec_store.get(args.spec_id)
    if not spec:
        print(f"❌ Specification {args.spec_id} not found", file=sys.stderr)
        sys.exit(1)

    print(f"\n📄 Generating {args.type} from spec: {spec.name}")

    # Initialize template manager
    try:
        template_manager = TemplateManager()
    except ImportError as e:
        print(f"❌ Template manager not available: {e}", file=sys.stderr)
        print("   Install jinja2: pip install jinja2")
        sys.exit(1)

    # Create template context
    context = TemplateContext(
        spec=spec,
        project_id=args.project_id,
        version=args.version or spec.version,
        author=args.author,
    )

    # Render template
    doc_type = DocumentType(args.type)
    try:
        content = template_manager.render(doc_type, context)
    except ValueError as e:
        print(f"❌ Template rendering failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Determine output file path
    if args.output:
        file_path = args.output
    else:
        # Auto-generate path based on doc type
        file_path = f"docs/{args.type}/{spec.name.lower().replace(' ', '-')}.md"

    # Create document
    doc = Document(
        project_id=args.project_id,
        name=args.name or f"{spec.name} Documentation",
        doc_type=doc_type,
        version=args.version or spec.version,
        status=DocumentStatus.DRAFT,
        content=content,
        file_path=file_path,
        description=args.description or f"Generated from {spec.name} specification",
        based_on_spec_ids=[args.spec_id],
        generated_by="template",
        author=args.author,
    )

    doc_id = doc_store.create(doc, write_to_file=not args.no_write_file)

    print(f"\n✅ Generated document {doc_id}: {doc.name}")
    print(f"   Type: {doc.doc_type.value}")
    print(f"   From spec: [{spec.id}] {spec.name}")
    if doc.file_path:
        print(f"   Saved to: {doc.file_path}")


def cmd_generate_ai(args):
    """Generate document using AI from specification."""
    db = get_database()
    doc_store = DocumentStore(db)
    spec_store = SpecificationStore(db)

    # Load specification
    spec = spec_store.get(args.spec_id)
    if not spec:
        print(f"❌ Specification {args.spec_id} not found", file=sys.stderr)
        sys.exit(1)

    print(f"\n🤖 Generating {args.type} from spec using AI: {spec.name}")

    # Initialize AI generator
    try:
        ai_generator = AIDocGenerator(
            api_key=args.api_key,
            model=args.model,
            temperature=args.temperature,
        )
    except ImportError as e:
        print(f"❌ AI generator not available: {e}", file=sys.stderr)
        print("   Install anthropic: pip install anthropic")
        sys.exit(1)

    # Assemble context
    print(f"   Assembling context...")
    assembler = ContextAssembler(spec_store=spec_store)
    context = assembler.assemble_for_spec(
        spec_id=args.spec_id,
        doc_type=DocumentType(args.type),
        include_related=not args.no_related,
        target_audience=args.audience,
        detail_level=args.detail_level,
    )

    print(f"   Context: {context.get_summary()}")

    # Generate documentation
    print(f"   Generating with {args.model}...")
    try:
        result = ai_generator.generate(
            doc_type=DocumentType(args.type),
            context=context,
            custom_instructions=args.instructions,
        )
    except Exception as e:
        print(f"❌ Generation failed: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"   Generated {len(result.content)} characters")
    print(f"   Tokens: {result.total_tokens} ({result.prompt_tokens} prompt + {result.completion_tokens} completion)")
    print(f"   Confidence: {result.confidence * 100:.0f}%")

    # Show warnings if any
    if result.warnings:
        print(f"\n⚠️  Quality Warnings:")
        for warning in result.warnings:
            print(f"   - {warning}")

    # Determine output file path
    if args.output:
        file_path = args.output
    else:
        # Auto-generate path based on doc type
        file_path = f"docs/{args.type}/{spec.name.lower().replace(' ', '-')}.md"

    # Convert to document and save
    doc = result.to_document(
        project_id=args.project_id,
        name=args.name or f"{spec.name} Documentation",
        version=args.version or spec.version,
        file_path=file_path,
        description=args.description or f"AI-generated {args.type} from {spec.name}",
        based_on_spec_ids=[args.spec_id],
        author=args.author,
    )

    doc_id = doc_store.create(doc, write_to_file=not args.no_write_file)

    print(f"\n✅ Generated AI document {doc_id}: {doc.name}")
    print(f"   Type: {doc.doc_type.value}")
    print(f"   Model: {result.model}")
    print(f"   From spec: [{spec.id}] {spec.name}")
    if doc.file_path:
        print(f"   Saved to: {doc.file_path}")

    # Preview content if requested
    if args.preview:
        print(f"\n{'=' * 80}")
        print(result.content[:500] + ("..." if len(result.content) > 500 else ""))
        print(f"{'=' * 80}")


def cmd_update(args):
    """Update an existing document."""
    db = get_database()
    store = DocumentStore(db)

    # Load document
    doc = store.get(args.doc_id)
    if not doc:
        print(f"❌ Document {args.doc_id} not found", file=sys.stderr)
        sys.exit(1)

    # Update fields
    if args.name:
        doc.name = args.name
    if args.version:
        doc.version = args.version
    if args.status:
        doc.status = DocumentStatus(args.status)
    if args.description:
        doc.description = args.description
    if args.content:
        doc.content = args.content
    elif args.file:
        file_path = Path(args.file)
        if file_path.exists():
            doc.content = file_path.read_text()

    # Update in database
    store.update(doc, write_to_file=not args.no_write_file)

    print(f"\n✅ Updated document {doc.id}: {doc.name}")
    print(f"   Version: {doc.version}")
    print(f"   Status: {doc.status.value}")


def cmd_delete(args):
    """Delete a document."""
    db = get_database()
    store = DocumentStore(db)

    # Load document first to show details
    doc = store.get(args.doc_id)
    if not doc:
        print(f"❌ Document {args.doc_id} not found", file=sys.stderr)
        sys.exit(1)

    # Confirm deletion
    if not args.yes:
        print(f"\n⚠️  Delete document {doc.id}: {doc.name}?")
        if doc.file_path:
            print(f"   File: {doc.file_path}")
        response = input("   Continue? [y/N]: ")
        if response.lower() != 'y':
            print("Cancelled.")
            sys.exit(0)

    # Delete
    success = store.delete(args.doc_id, delete_file=args.delete_file)

    if success:
        print(f"\n✅ Deleted document {args.doc_id}")
        if args.delete_file:
            print(f"   Deleted file: {doc.file_path}")
    else:
        print(f"❌ Failed to delete document", file=sys.stderr)
        sys.exit(1)


def cmd_show(args):
    """Show document details."""
    db = get_database()
    store = DocumentStore(db)

    doc = store.get(args.doc_id)
    if not doc:
        print(f"❌ Document {args.doc_id} not found", file=sys.stderr)
        sys.exit(1)

    if args.json:
        output = {
            "id": doc.id,
            "name": doc.name,
            "type": doc.doc_type.value,
            "version": doc.version,
            "status": doc.status.value,
            "file_path": doc.file_path,
            "description": doc.description,
            "based_on_spec_ids": doc.based_on_spec_ids,
            "based_on_doc_ids": doc.based_on_doc_ids,
            "related_adr_ids": doc.related_adr_ids,
            "generated_by": doc.generated_by,
            "generation_model": doc.generation_model,
            "author": doc.author,
            "reviewers": doc.reviewers,
            "tags": doc.tags,
            "created_at": doc.created_at.isoformat(),
            "updated_at": doc.updated_at.isoformat(),
        }
        if args.content:
            output["content"] = doc.content
        print(json.dumps(output, indent=2))
    else:
        print(f"\n📄 Document {doc.id}: {doc.name}")
        print("=" * 80)
        print(f"Type: {doc.doc_type.value}")
        print(f"Version: {doc.version}")
        print(f"Status: {doc.status.value}")
        if doc.description:
            print(f"Description: {doc.description}")
        if doc.file_path:
            print(f"File: {doc.file_path}")
        if doc.based_on_spec_ids:
            print(f"Based on specs: {doc.based_on_spec_ids}")
        if doc.based_on_doc_ids:
            print(f"Based on docs: {doc.based_on_doc_ids}")
        if doc.related_adr_ids:
            print(f"Related ADRs: {doc.related_adr_ids}")
        if doc.generated_by:
            print(f"Generated by: {doc.generated_by}")
            if doc.generation_model:
                print(f"Model: {doc.generation_model}")
        if doc.author:
            print(f"Author: {doc.author}")
        if doc.reviewers:
            print(f"Reviewers: {', '.join(doc.reviewers)}")
        if doc.tags:
            print(f"Tags: {', '.join(doc.tags)}")
        print(f"Created: {doc.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Updated: {doc.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")

        if args.content:
            print("\nContent:")
            print("-" * 80)
            print(doc.content[:500] + ("..." if len(doc.content) > 500 else ""))


def cmd_templates(args):
    """List available templates."""
    try:
        template_manager = TemplateManager()
    except ImportError as e:
        print(f"❌ Template manager not available: {e}", file=sys.stderr)
        sys.exit(1)

    templates = template_manager.list_templates(category=args.category)

    print(f"\n📋 Available Templates")
    if args.category:
        print(f"   Category: {args.category}")
    print("=" * 80)

    for template in templates:
        print(f"  • {template}")

    print(f"\nTotal: {len(templates)} templates")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Manage generated documentation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    subparsers.required = True

    # List command
    list_parser = subparsers.add_parser("list", help="List documents")
    list_parser.add_argument("--project-id", type=int, default=1, help="Project ID (default: 1)")
    list_parser.add_argument("--type", help="Filter by document type")
    list_parser.add_argument("--status", help="Filter by status")
    list_parser.add_argument("--limit", type=int, default=100, help="Limit results (default: 100)")
    list_parser.add_argument("--json", action="store_true", help="Output as JSON")
    list_parser.set_defaults(func=cmd_list)

    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new document")
    create_parser.add_argument("--name", required=True, help="Document name")
    create_parser.add_argument("--type", required=True, help="Document type (e.g., api_doc, tdd)")
    create_parser.add_argument("--project-id", type=int, default=1, help="Project ID")
    create_parser.add_argument("--version", default="1.0.0", help="Version (default: 1.0.0)")
    create_parser.add_argument("--status", default="draft", help="Status (default: draft)")
    create_parser.add_argument("--file", help="Read content from file")
    create_parser.add_argument("--content", help="Document content")
    create_parser.add_argument("--description", help="Description")
    create_parser.add_argument("--author", help="Author name")
    create_parser.add_argument("--no-write-file", action="store_true", help="Don't write to filesystem")
    create_parser.set_defaults(func=cmd_create)

    # Generate command
    gen_parser = subparsers.add_parser("generate", help="Generate document from specification")
    gen_parser.add_argument("--spec-id", type=int, required=True, help="Specification ID")
    gen_parser.add_argument("--type", required=True, help="Document type to generate")
    gen_parser.add_argument("--project-id", type=int, default=1, help="Project ID")
    gen_parser.add_argument("--name", help="Document name (default: auto-generated)")
    gen_parser.add_argument("--version", help="Version (default: spec version)")
    gen_parser.add_argument("--output", help="Output file path (default: auto-generated)")
    gen_parser.add_argument("--description", help="Description")
    gen_parser.add_argument("--author", help="Author name")
    gen_parser.add_argument("--no-write-file", action="store_true", help="Don't write to filesystem")
    gen_parser.set_defaults(func=cmd_generate)

    # Generate AI command
    ai_parser = subparsers.add_parser("generate-ai", help="Generate document using AI from specification")
    ai_parser.add_argument("--spec-id", type=int, required=True, help="Specification ID")
    ai_parser.add_argument("--type", required=True, help="Document type to generate")
    ai_parser.add_argument("--project-id", type=int, default=1, help="Project ID")
    ai_parser.add_argument("--name", help="Document name (default: auto-generated)")
    ai_parser.add_argument("--version", help="Version (default: spec version)")
    ai_parser.add_argument("--output", help="Output file path (default: auto-generated)")
    ai_parser.add_argument("--description", help="Description")
    ai_parser.add_argument("--author", help="Author name")
    ai_parser.add_argument("--model", default="claude-3-5-sonnet-20241022", help="Claude model to use")
    ai_parser.add_argument("--temperature", type=float, default=0.7, help="Generation temperature (0-1)")
    ai_parser.add_argument("--api-key", help="Anthropic API key (uses ANTHROPIC_API_KEY env var if not provided)")
    ai_parser.add_argument("--instructions", help="Custom instructions for generation")
    ai_parser.add_argument("--audience", default="technical", help="Target audience (technical/business/executive)")
    ai_parser.add_argument("--detail-level", default="comprehensive", help="Detail level (brief/standard/comprehensive)")
    ai_parser.add_argument("--no-related", action="store_true", help="Don't include related specs")
    ai_parser.add_argument("--no-write-file", action="store_true", help="Don't write to filesystem")
    ai_parser.add_argument("--preview", action="store_true", help="Show content preview")
    ai_parser.set_defaults(func=cmd_generate_ai)

    # Update command
    update_parser = subparsers.add_parser("update", help="Update an existing document")
    update_parser.add_argument("--doc-id", type=int, required=True, help="Document ID")
    update_parser.add_argument("--name", help="New name")
    update_parser.add_argument("--version", help="New version")
    update_parser.add_argument("--status", help="New status")
    update_parser.add_argument("--file", help="Read content from file")
    update_parser.add_argument("--content", help="New content")
    update_parser.add_argument("--description", help="New description")
    update_parser.add_argument("--no-write-file", action="store_true", help="Don't write to filesystem")
    update_parser.set_defaults(func=cmd_update)

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a document")
    delete_parser.add_argument("--doc-id", type=int, required=True, help="Document ID")
    delete_parser.add_argument("--delete-file", action="store_true", help="Also delete file")
    delete_parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")
    delete_parser.set_defaults(func=cmd_delete)

    # Show command
    show_parser = subparsers.add_parser("show", help="Show document details")
    show_parser.add_argument("--doc-id", type=int, required=True, help="Document ID")
    show_parser.add_argument("--content", action="store_true", help="Include content")
    show_parser.add_argument("--json", action="store_true", help="Output as JSON")
    show_parser.set_defaults(func=cmd_show)

    # Templates command
    templates_parser = subparsers.add_parser("templates", help="List available templates")
    templates_parser.add_argument("--category", help="Filter by category (e.g., api, technical)")
    templates_parser.set_defaults(func=cmd_templates)

    # Parse arguments and run command
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
