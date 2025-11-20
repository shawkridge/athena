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
    check-drift     Check for drift between documents and specs
    diff            Show diff for document regeneration (preview changes)
    sync            Sync documents with their source specifications
    check-conflict  Check if document has manual edits that conflict
    resolve-conflict Resolve conflicts between manual edits and AI
    mark-manual     Mark or unmark document as manual override

Examples:
    # List all documents
    athena-doc-manage list

    # Generate API docs from spec (template-based)
    athena-doc-manage generate --spec-id 5 --type api_doc --output docs/api.md

    # Generate TDD using AI
    athena-doc-manage generate-ai --spec-id 5 --type tdd --preview

    # Check drift for all documents in project
    athena-doc-manage check-drift --project-id 1

    # Show diff for a document (preview what would change)
    athena-doc-manage diff --doc-id 5

    # Sync with preview (show diff first, then ask for confirmation)
    athena-doc-manage sync --doc-id 5 --preview

    # Sync all drifted documents (dry run)
    athena-doc-manage sync --project-id 1 --dry-run

    # Sync specific document
    athena-doc-manage sync --doc-id 5

    # Create manual document
    athena-doc-manage create --name "Deployment Guide" --type deployment --file ops/deploy.md

    # List available templates
    athena-doc-manage templates --category api

    # Show document details
    athena-doc-manage show --doc-id 10

    # Check if document has manual edits
    athena-doc-manage check-conflict --doc-id 5

    # Resolve conflict using 3-way merge
    athena-doc-manage resolve-conflict --doc-id 5 --strategy merge

    # Mark document as manual override (skip auto-sync)
    athena-doc-manage mark-manual --doc-id 5

    # Clear manual override (resume auto-sync)
    athena-doc-manage mark-manual --doc-id 5 --clear
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
from athena.architecture.sync import (
    DriftDetector,
    SyncManager,
    StalenessChecker,
    DocumentDiffer,
    ConflictDetector,
    ConflictResolver,
    MergeStrategy,
)


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


def cmd_check_drift(args):
    """Check for drift between documents and specifications."""
    db = get_database()
    doc_store = DocumentStore(db)
    spec_store = SpecificationStore(db)

    detector = DriftDetector(spec_store, doc_store)

    if args.doc_id:
        # Check single document
        try:
            result = detector.check_document(
                doc_id=args.doc_id,
                staleness_threshold_days=args.staleness_days
            )

            if args.json:
                print(json.dumps(result.to_dict(), indent=2))
            else:
                print(f"\n📊 Drift Check: {result.document.name}")
                print("=" * 80)
                print(f"Status: {result.status.value}")
                print(f"Message: {result.message}")
                if result.stored_hash:
                    print(f"Stored hash: {result.stored_hash}")
                if result.current_hash:
                    print(f"Current hash: {result.current_hash}")
                if result.spec_ids:
                    print(f"Source specs: {result.spec_ids}")
                if result.last_synced_at:
                    print(f"Last synced: {result.last_synced_at.strftime('%Y-%m-%d %H:%M:%S')}")
                if result.days_since_sync is not None:
                    print(f"Days since sync: {result.days_since_sync}")
                print(f"\nRecommendation: {result.recommendation}")

                if result.needs_regeneration:
                    print(f"\n⚠️  Document needs regeneration")

        except Exception as e:
            print(f"❌ Error checking drift: {e}", file=sys.stderr)
            sys.exit(1)

    else:
        # Check all documents in project
        results = detector.check_project(
            project_id=args.project_id,
            staleness_threshold_days=args.staleness_days
        )

        if args.json:
            output = [r.to_dict() for r in results]
            print(json.dumps(output, indent=2))
        else:
            print(f"\n📊 Drift Check (Project {args.project_id})")
            print("=" * 80)

            # Group by status
            by_status = {}
            for result in results:
                status = result.status.value
                if status not in by_status:
                    by_status[status] = []
                by_status[status].append(result)

            # Display summary
            in_sync = len(by_status.get('in_sync', []))
            drifted = len(by_status.get('drifted', []))
            stale = len(by_status.get('stale', []))
            missing_hash = len(by_status.get('missing_hash', []))
            orphaned = len(by_status.get('orphaned', []))

            print(f"\nSummary:")
            print(f"  ✅ In sync: {in_sync}")
            print(f"  ⚠️  Drifted: {drifted}")
            print(f"  ⏰ Stale: {stale}")
            print(f"  ❓ Missing hash: {missing_hash}")
            print(f"  🗑️  Orphaned: {orphaned}")

            # List documents needing attention
            needs_attention = [r for r in results if r.needs_regeneration]
            if needs_attention:
                print(f"\n⚠️  Documents Needing Attention ({len(needs_attention)}):")
                print("-" * 80)
                for result in needs_attention[:10]:  # Show first 10
                    print(f"\n[{result.document.id}] {result.document.name}")
                    print(f"    Status: {result.status.value}")
                    print(f"    {result.message}")

                if len(needs_attention) > 10:
                    print(f"\n... and {len(needs_attention) - 10} more")

                print(f"\nRun with --json to see full details")
            else:
                print(f"\n✅ All documents are in sync!")


def cmd_diff(args):
    """Show diff for document regeneration."""
    db = get_database()
    doc_store = DocumentStore(db)
    spec_store = SpecificationStore(db)

    # Get document
    doc = doc_store.get(args.doc_id)
    if not doc:
        print(f"❌ Document {args.doc_id} not found", file=sys.stderr)
        sys.exit(1)

    # Initialize AI generator to compute what new content would be
    try:
        ai_generator = AIDocGenerator(
            api_key=args.api_key,
            model=args.model
        )
    except ImportError:
        print(f"❌ AI generator not available - cannot compute diff", file=sys.stderr)
        sys.exit(1)

    # Generate new content (without saving)
    try:
        assembler = ContextAssembler(spec_store=spec_store)

        if not doc.based_on_spec_ids:
            print(f"❌ Document has no source specifications", file=sys.stderr)
            sys.exit(1)

        # Assemble context from specs
        context = assembler.assemble_for_specs(doc.based_on_spec_ids)

        # Generate new content
        print(f"🤖 Generating new content to compare...")
        result = ai_generator.generate(
            doc_type=doc.doc_type,
            context=context
        )
        new_content = result.content

    except Exception as e:
        print(f"❌ Failed to generate content: {e}", file=sys.stderr)
        sys.exit(1)

    # Compute diff
    differ = DocumentDiffer(spec_store=spec_store, doc_store=doc_store)
    diff_result = differ.compute_diff(
        doc_id=args.doc_id,
        new_content=new_content,
        show_cause=args.show_cause
    )

    # Output
    if args.json:
        print(json.dumps(diff_result.to_json(), indent=2))
    elif args.markdown:
        print(diff_result.to_markdown())
    else:
        # Rich terminal output
        print(diff_result.to_text(color=not args.no_color, show_unchanged=args.show_unchanged))

        # Actionable next steps
        if diff_result.has_changes:
            print("\n💡 Next Steps:")
            print(f"   To apply these changes, run:")
            print(f"   athena-doc-manage sync --doc-id {args.doc_id}")
        else:
            print("\n✅ No changes detected - document is up to date")


def cmd_sync(args):
    """Sync documents with their source specifications."""
    db = get_database()
    doc_store = DocumentStore(db)
    spec_store = SpecificationStore(db)

    # Initialize AI generator if needed
    ai_generator = None
    if not args.dry_run and not args.manual_only:
        try:
            ai_generator = AIDocGenerator(
                api_key=args.api_key,
                model=args.model
            )
        except ImportError:
            print(f"⚠️  AI generator not available - will mark for manual review", file=sys.stderr)

    # Initialize sync manager
    sync_manager = SyncManager(
        spec_store=spec_store,
        doc_store=doc_store,
        ai_generator=ai_generator
    )

    # Determine strategy
    from athena.architecture.sync.sync_manager import SyncStrategy
    if args.manual_only:
        strategy = SyncStrategy.MANUAL
    elif args.skip:
        strategy = SyncStrategy.SKIP
    else:
        strategy = SyncStrategy.REGENERATE

    if args.doc_id:
        # Sync single document
        try:
            # Preview mode: show diff before syncing
            if hasattr(args, 'preview') and args.preview and not args.dry_run:
                # Get document
                doc = doc_store.get(args.doc_id)
                if not doc:
                    print(f"❌ Document {args.doc_id} not found", file=sys.stderr)
                    sys.exit(1)

                # Generate new content to compare
                if ai_generator and doc.based_on_spec_ids:
                    try:
                        assembler = ContextAssembler(spec_store=spec_store)
                        context = assembler.assemble_for_specs(doc.based_on_spec_ids)

                        print(f"\n🤖 Generating new content for preview...")
                        gen_result = ai_generator.generate(
                            doc_type=doc.doc_type,
                            context=context
                        )
                        new_content = gen_result.content

                        # Compute diff
                        differ = DocumentDiffer(spec_store=spec_store, doc_store=doc_store)
                        diff_result = differ.compute_diff(
                            doc_id=args.doc_id,
                            new_content=new_content,
                            show_cause=True
                        )

                        # Show diff
                        print(diff_result.to_text(color=True, show_unchanged=False))

                        # Ask for confirmation (unless --yes flag)
                        if not hasattr(args, 'yes') or not args.yes:
                            if diff_result.has_changes:
                                response = input("\n❓ Apply these changes? [y/N] ")
                                if response.lower() != 'y':
                                    print("❌ Sync cancelled")
                                    sys.exit(0)
                            else:
                                print("\n✅ No changes to apply")
                                sys.exit(0)

                    except Exception as e:
                        print(f"⚠️  Preview failed: {e}", file=sys.stderr)
                        print(f"   Proceeding with sync anyway...")

            result = sync_manager.sync_document(
                doc_id=args.doc_id,
                strategy=strategy,
                dry_run=args.dry_run
            )

            if args.json:
                print(json.dumps(result.to_dict(), indent=2))
            else:
                print(f"\n🔄 Sync Result: {result.document.name}")
                print("=" * 80)
                print(f"Strategy: {result.strategy.value}")
                print(f"Success: {result.success}")
                if result.regenerated:
                    print(f"Regenerated: Yes")
                    if result.generation_time_seconds:
                        print(f"Generation time: {result.generation_time_seconds:.1f}s")
                if result.old_hash:
                    print(f"Old hash: {result.old_hash}")
                if result.new_hash:
                    print(f"New hash: {result.new_hash}")
                print(f"Message: {result.message}")

                if result.success and result.regenerated:
                    print(f"\n✅ Document successfully synced")
                elif result.error:
                    print(f"\n❌ Error: {result.error}")

        except Exception as e:
            print(f"❌ Sync failed: {e}", file=sys.stderr)
            sys.exit(1)

    else:
        # Sync all documents in project
        results = sync_manager.sync_project(
            project_id=args.project_id,
            strategy=strategy,
            dry_run=args.dry_run,
            staleness_threshold_days=args.staleness_days
        )

        if args.json:
            output = [r.to_dict() for r in results]
            print(json.dumps(output, indent=2))
        else:
            summary = sync_manager.get_sync_summary(results)

            print(f"\n🔄 Sync Results (Project {args.project_id})")
            if args.dry_run:
                print("   (DRY RUN - no changes made)")
            print("=" * 80)

            print(f"\nSummary:")
            print(f"  Total documents: {summary['total']}")
            print(f"  ✅ Successful: {summary['successful']}")
            print(f"  ❌ Failed: {summary['failed']}")
            print(f"  🔄 Regenerated: {summary['regenerated']}")
            print(f"  ⏭️  Skipped: {summary['skipped']}")
            print(f"  ✋ Manual review: {summary['manual_review_needed']}")

            if summary['regenerated'] > 0:
                print(f"\nGeneration Stats:")
                print(f"  Total time: {summary['total_generation_time_seconds']:.1f}s")
                print(f"  Average time: {summary['average_generation_time_seconds']:.1f}s")

            # Show failures
            failures = [r for r in results if not r.success]
            if failures:
                print(f"\n❌ Failed Documents ({len(failures)}):")
                for result in failures[:5]:
                    print(f"  - {result.document.name}: {result.error or result.message}")
                if len(failures) > 5:
                    print(f"  ... and {len(failures) - 5} more")

            if args.dry_run and summary['total'] > 0:
                print(f"\n💡 Run without --dry-run to actually sync documents")


def cmd_check_conflict(args):
    """Check if document has manual edits that conflict with specifications."""
    db = get_database()
    doc_store = DocumentStore(db)
    detector = ConflictDetector(doc_store)

    try:
        result = detector.detect_conflict(args.doc_id)

        if args.json:
            output = {
                "document_id": result.document.id,
                "document_name": result.document.name,
                "status": result.status.value,
                "has_manual_edits": result.has_manual_edits,
                "ai_baseline_hash": result.ai_baseline_hash,
                "current_hash": result.current_hash,
                "manual_edit_timestamp": result.manual_edit_timestamp.isoformat() if result.manual_edit_timestamp else None,
                "conflicting_sections": result.conflicting_sections,
                "recommendation": result.recommendation.value,
                "message": result.message,
            }
            print(json.dumps(output, indent=2))
        else:
            print(f"\n📄 Document: {result.document.name}")
            print("=" * 80)
            print(f"Status: {result.status.value}")
            print(f"Has manual edits: {'Yes' if result.has_manual_edits else 'No'}")

            if result.ai_baseline_hash:
                print(f"AI baseline hash: {result.ai_baseline_hash}")
                print(f"Current hash: {result.current_hash}")

            if result.manual_edit_timestamp:
                print(f"Last manual edit: {result.manual_edit_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

            if result.conflicting_sections:
                print(f"\nConflicting sections:")
                for section in result.conflicting_sections:
                    print(f"  - {section}")

            print(f"\nRecommendation: {result.recommendation.value}")
            print(f"Message: {result.message}")

            if result.needs_resolution:
                print(f"\n⚠️  This document needs conflict resolution before syncing")
                print(f"   Use: athena-doc-manage resolve-conflict --doc-id {args.doc_id} --strategy {result.recommendation.value}")
            else:
                print(f"\n✅ No conflicts detected - safe to sync")

    except ValueError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_resolve_conflict(args):
    """Resolve conflicts between manual edits and AI regeneration."""
    db = get_database()
    doc_store = DocumentStore(db)
    spec_store = SpecificationStore(db)
    resolver = ConflictResolver(doc_store)

    # Get document
    doc = doc_store.get(args.doc_id)
    if not doc:
        print(f"❌ Document {args.doc_id} not found", file=sys.stderr)
        sys.exit(1)

    # Parse strategy
    strategy = MergeStrategy(args.strategy)

    # For merge strategies that need new AI content, generate it
    new_ai_content = None
    if strategy in (MergeStrategy.KEEP_AI, MergeStrategy.THREE_WAY_MERGE):
        if not doc.based_on_spec_ids:
            print(f"❌ Document has no source specifications - cannot regenerate", file=sys.stderr)
            sys.exit(1)

        try:
            # Initialize AI generator
            ai_generator = AIDocGenerator(
                api_key=args.api_key,
                model=args.model
            )

            # Assemble context
            assembler = ContextAssembler(spec_store=spec_store)
            context = assembler.assemble_for_specs(doc.based_on_spec_ids)

            # Generate new content
            print(f"\n🤖 Generating new AI content...")
            gen_result = ai_generator.generate(
                doc_type=doc.doc_type,
                context=context
            )
            new_ai_content = gen_result.content

        except Exception as e:
            print(f"❌ AI generation failed: {e}", file=sys.stderr)
            sys.exit(1)

    # Resolve conflict
    try:
        result = resolver.resolve_conflict(
            doc_id=args.doc_id,
            new_ai_content=new_ai_content or "",
            strategy=strategy
        )

        if args.json:
            output = {
                "success": result.success,
                "strategy": result.strategy.value,
                "needs_review": result.needs_review,
                "message": result.message,
                "conflicts": result.conflicts,
                "sections_merged": result.sections_merged,
                "sections_conflicted": result.sections_conflicted,
                "manual_sections_kept": result.manual_sections_kept,
                "ai_sections_kept": result.ai_sections_kept,
            }
            print(json.dumps(output, indent=2))
        else:
            print(f"\n🔀 Conflict Resolution Result")
            print("=" * 80)
            print(f"Strategy: {result.strategy.value}")
            print(f"Success: {'Yes' if result.success else 'No'}")
            print(f"Needs review: {'Yes' if result.needs_review else 'No'}")
            print(f"Message: {result.message}")

            if result.sections_merged > 0:
                print(f"\nMerge Statistics:")
                print(f"  Sections merged: {result.sections_merged}")
                print(f"  Manual sections kept: {result.manual_sections_kept}")
                print(f"  AI sections kept: {result.ai_sections_kept}")
                print(f"  Conflicted sections: {result.sections_conflicted}")

            if result.conflicts:
                print(f"\n⚠️  Conflicts detected ({len(result.conflicts)}):")
                for conflict in result.conflicts[:10]:
                    print(f"  - {conflict}")
                if len(result.conflicts) > 10:
                    print(f"  ... and {len(result.conflicts) - 10} more")

            if result.success and result.merged_content:
                if not args.dry_run:
                    # Apply merged content
                    doc.content = result.merged_content
                    doc_store.update(doc, write_to_file=True)
                    print(f"\n✅ Merged content applied to document")
                else:
                    print(f"\n💡 Dry run - no changes made")
                    print(f"   Run without --dry-run to apply changes")

            elif result.needs_review:
                print(f"\n⚠️  Manual review required - conflicts could not be auto-resolved")
                if result.merged_content:
                    print(f"   Merged content available but needs human verification")
                print(f"   Use --dry-run to preview changes before applying")

    except ValueError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_mark_manual(args):
    """Mark or unmark document as manual override."""
    db = get_database()
    doc_store = DocumentStore(db)
    detector = ConflictDetector(doc_store)

    try:
        if args.clear:
            # Clear manual override flag
            success = detector.clear_manual_flag(args.doc_id)
            if success:
                print(f"✅ Manual override flag cleared for document {args.doc_id}")
                print(f"   Document will now be included in auto-sync")
        else:
            # Set manual override flag
            success = detector.mark_manual_override(args.doc_id)
            if success:
                print(f"✅ Document {args.doc_id} marked as manual override")
                print(f"   This document will be skipped in auto-sync")
                print(f"   Use --clear to resume auto-sync")

    except ValueError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


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

    # Check-drift command
    drift_parser = subparsers.add_parser("check-drift", help="Check for drift between documents and specs")
    drift_parser.add_argument("--project-id", type=int, default=1, help="Project ID (default: 1)")
    drift_parser.add_argument("--doc-id", type=int, help="Check specific document ID")
    drift_parser.add_argument("--staleness-days", type=int, default=30, help="Staleness threshold in days (default: 30)")
    drift_parser.add_argument("--json", action="store_true", help="Output as JSON")
    drift_parser.set_defaults(func=cmd_check_drift)

    # Diff command
    diff_parser = subparsers.add_parser("diff", help="Show diff for document regeneration")
    diff_parser.add_argument("--doc-id", type=int, required=True, help="Document ID to diff")
    diff_parser.add_argument("--show-cause", action="store_true", default=True, help="Show spec changes that caused drift")
    diff_parser.add_argument("--show-unchanged", action="store_true", help="Show unchanged sections")
    diff_parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    diff_parser.add_argument("--model", default="claude-3-5-sonnet-20241022", help="Claude model to use for generation")
    diff_parser.add_argument("--api-key", help="Anthropic API key (uses ANTHROPIC_API_KEY env var if not provided)")
    diff_parser.add_argument("--json", action="store_true", help="Output as JSON")
    diff_parser.add_argument("--markdown", action="store_true", help="Output as Markdown")
    diff_parser.set_defaults(func=cmd_diff)

    # Sync command
    sync_parser = subparsers.add_parser("sync", help="Sync documents with source specifications")
    sync_parser.add_argument("--project-id", type=int, default=1, help="Project ID (default: 1)")
    sync_parser.add_argument("--doc-id", type=int, help="Sync specific document ID")
    sync_parser.add_argument("--dry-run", action="store_true", help="Check what would be synced without doing it")
    sync_parser.add_argument("--preview", action="store_true", help="Show diff before syncing and ask for confirmation")
    sync_parser.add_argument("--yes", "-y", action="store_true", help="Auto-confirm (skip confirmation prompt)")
    sync_parser.add_argument("--staleness-days", type=int, default=30, help="Staleness threshold in days (default: 30)")
    sync_parser.add_argument("--manual-only", action="store_true", help="Mark for manual review instead of regenerating")
    sync_parser.add_argument("--skip", action="store_true", help="Skip sync (for testing)")
    sync_parser.add_argument("--model", default="claude-3-5-sonnet-20241022", help="Claude model to use for regeneration")
    sync_parser.add_argument("--api-key", help="Anthropic API key (uses ANTHROPIC_API_KEY env var if not provided)")
    sync_parser.add_argument("--json", action="store_true", help="Output as JSON")
    sync_parser.set_defaults(func=cmd_sync)

    # Check-conflict command
    check_conflict_parser = subparsers.add_parser("check-conflict", help="Check if document has manual edits")
    check_conflict_parser.add_argument("--doc-id", type=int, required=True, help="Document ID to check")
    check_conflict_parser.add_argument("--json", action="store_true", help="Output as JSON")
    check_conflict_parser.set_defaults(func=cmd_check_conflict)

    # Resolve-conflict command
    resolve_conflict_parser = subparsers.add_parser("resolve-conflict", help="Resolve conflicts between manual edits and AI regeneration")
    resolve_conflict_parser.add_argument("--doc-id", type=int, required=True, help="Document ID with conflict")
    resolve_conflict_parser.add_argument("--strategy", required=True,
                                        choices=["keep_manual", "keep_ai", "merge", "manual_review"],
                                        help="Conflict resolution strategy")
    resolve_conflict_parser.add_argument("--model", default="claude-3-5-sonnet-20241022", help="Claude model to use for AI generation")
    resolve_conflict_parser.add_argument("--api-key", help="Anthropic API key (uses ANTHROPIC_API_KEY env var if not provided)")
    resolve_conflict_parser.add_argument("--dry-run", action="store_true", help="Preview resolution without applying")
    resolve_conflict_parser.add_argument("--json", action="store_true", help="Output as JSON")
    resolve_conflict_parser.set_defaults(func=cmd_resolve_conflict)

    # Mark-manual command
    mark_manual_parser = subparsers.add_parser("mark-manual", help="Mark or unmark document as manual override")
    mark_manual_parser.add_argument("--doc-id", type=int, required=True, help="Document ID")
    mark_manual_parser.add_argument("--clear", action="store_true", help="Clear manual override flag (resume auto-sync)")
    mark_manual_parser.set_defaults(func=cmd_mark_manual)

    # Parse arguments and run command
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
