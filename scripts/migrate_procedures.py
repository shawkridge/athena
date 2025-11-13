#!/usr/bin/env python3
"""Migrate 101 procedures from database to git-backed storage.

This script:
1. Connects to the Athena memory database
2. Extracts all procedures from procedural store
3. Generates executable code from procedure templates
4. Stores procedures in git with version history
5. Reports migration results and any issues
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from athena.core.database import Database
from athena.procedural.store import ProceduralStore
from athena.procedural.git_store import GitBackedProcedureStore
from athena.procedural.code_extractor import ProcedureCodeExtractor
from athena.procedural.models import ExecutableProcedure, ProcedureCategory

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def migrate_procedures(
    db_path: str = "~/.claude/memory.db",
    git_repo_path: str = None,
    dry_run: bool = False,
) -> Dict:
    """Migrate procedures from database to git.

    Args:
        db_path: Path to Athena memory database
        git_repo_path: Path to git repository for procedures (default: project root)
        dry_run: If True, simulate migration without writing

    Returns:
        Migration report dict with statistics
    """
    # Expand paths
    db_path = Path(db_path).expanduser()
    if not git_repo_path:
        git_repo_path = project_root

    git_repo_path = Path(git_repo_path).expanduser()

    logger.info(f"Starting procedure migration...")
    logger.info(f"Database: {db_path}")
    logger.info(f"Git repo: {git_repo_path}")
    logger.info(f"Dry run: {dry_run}")

    report = {
        "start_time": datetime.now(),
        "database_path": str(db_path),
        "git_repo_path": str(git_repo_path),
        "dry_run": dry_run,
        "total_procedures": 0,
        "migrated": 0,
        "failed": 0,
        "skipped": 0,
        "errors": [],
        "procedure_details": [],
    }

    try:
        # Connect to database
        if not db_path.exists():
            logger.error(f"Database not found: {db_path}")
            report["errors"].append(f"Database not found: {db_path}")
            return report

        logger.info("Connecting to database...")
        db = Database(str(db_path))
        procedural_store = ProceduralStore(db)

        # List all procedures
        all_procedures = procedural_store.list_procedures()
        logger.info(f"Found {len(all_procedures)} procedures in database")
        report["total_procedures"] = len(all_procedures)

        # Initialize git store
        if not dry_run:
            logger.info("Initializing git store...")
            git_store = GitBackedProcedureStore(str(git_repo_path))

        # Migrate each procedure
        for i, procedure in enumerate(all_procedures, 1):
            try:
                logger.info(f"[{i}/{len(all_procedures)}] Migrating: {procedure.name}")

                # Extract code from procedure
                extractor = ProcedureCodeExtractor(procedure)
                code, confidence = extractor.extract()

                if not code:
                    logger.warning(f"  → Failed to extract code, confidence: {confidence:.2f}")
                    report["failed"] += 1
                    report["errors"].append(f"Code extraction failed for {procedure.name}")
                    continue

                # Create ExecutableProcedure
                exec_proc = ExecutableProcedure(
                    procedure_id=procedure.id or i,
                    name=procedure.name,
                    category=procedure.category,
                    code=code,
                    code_version="1.0.0",
                    code_language="python",
                    code_generated_at=procedure.created_at,
                    code_generation_confidence=confidence,
                    description=procedure.description,
                )

                if not exec_proc.id:
                    exec_proc.id = procedure.id or i

                # Store in git
                if not dry_run:
                    try:
                        git_hash = git_store.store_procedure(
                            exec_proc,
                            author="migration-script",
                            commit_message=f"Migrate procedure {exec_proc.name} (confidence: {confidence:.2f})",
                        )
                        logger.info(f"  ✓ Migrated to git ({git_hash}), confidence: {confidence:.2f}")
                        report["migrated"] += 1
                    except Exception as e:
                        logger.error(f"  ✗ Git storage failed: {e}")
                        report["failed"] += 1
                        report["errors"].append(f"Git storage failed for {procedure.name}: {str(e)}")
                        continue
                else:
                    logger.info(f"  [DRY RUN] Would migrate with confidence: {confidence:.2f}")
                    report["migrated"] += 1

                # Record procedure details
                report["procedure_details"].append({
                    "id": exec_proc.id,
                    "name": exec_proc.name,
                    "category": exec_proc.category,
                    "confidence": confidence,
                    "code_length": len(code),
                    "status": "migrated",
                })

            except Exception as e:
                logger.error(f"  ✗ Unexpected error: {e}")
                report["failed"] += 1
                report["errors"].append(f"Unexpected error migrating {procedure.name}: {str(e)}")
                continue

        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("MIGRATION SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Total procedures:     {report['total_procedures']}")
        logger.info(f"Migrated:             {report['migrated']}")
        logger.info(f"Failed:               {report['failed']}")
        logger.info(f"Skipped:              {report['skipped']}")
        logger.info(f"Success rate:         {report['migrated']/max(report['total_procedures'], 1)*100:.1f}%")

        if report["errors"]:
            logger.warning("\nERRORS:")
            for error in report["errors"]:
                logger.warning(f"  - {error}")

        if not dry_run and report['migrated'] > 0:
            logger.info(f"\n✓ Successfully migrated {report['migrated']} procedures to git")
            logger.info(f"  Location: {git_repo_path}/procedures")

        report["end_time"] = datetime.now()
        report["duration"] = (report["end_time"] - report["start_time"]).total_seconds()

        return report

    except Exception as e:
        logger.error(f"Migration failed with error: {e}", exc_info=True)
        report["errors"].append(f"Critical error: {str(e)}")
        report["end_time"] = datetime.now()
        return report


def print_report(report: Dict):
    """Print migration report.

    Args:
        report: Migration report dict
    """
    print("\n" + "=" * 70)
    print("ATHENA PROCEDURE MIGRATION REPORT")
    print("=" * 70)
    print(f"Started:     {report['start_time'].isoformat()}")
    print(f"Completed:   {report['end_time'].isoformat()}")
    print(f"Duration:    {report['duration']:.1f}s")
    print(f"Database:    {report['database_path']}")
    print(f"Git Repo:    {report['git_repo_path']}")
    print(f"Dry Run:     {report['dry_run']}")
    print()
    print(f"Total:       {report['total_procedures']}")
    print(f"Migrated:    {report['migrated']} ✓")
    print(f"Failed:      {report['failed']} ✗")
    print(f"Skipped:     {report['skipped']} -")
    print()
    success_rate = report['migrated'] / max(report['total_procedures'], 1) * 100
    print(f"Success Rate: {success_rate:.1f}%")
    print("=" * 70)

    if report["errors"]:
        print("\nERRORS:")
        for i, error in enumerate(report["errors"], 1):
            print(f"{i}. {error}")


if __name__ == "__main__":
    import argparse
    from typing import Dict

    parser = argparse.ArgumentParser(
        description="Migrate Athena procedures from database to git storage"
    )
    parser.add_argument(
        "--db",
        type=str,
        default="~/.claude/memory.db",
        help="Path to Athena memory database",
    )
    parser.add_argument(
        "--git-repo",
        type=str,
        default=None,
        help="Path to git repository (default: project root)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate migration without writing",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output report as JSON",
    )

    args = parser.parse_args()

    try:
        report = migrate_procedures(
            db_path=args.db,
            git_repo_path=args.git_repo,
            dry_run=args.dry_run,
        )

        if args.json:
            import json
            # Convert datetime to string for JSON serialization
            report_json = {k: str(v) if isinstance(v, datetime) else v for k, v in report.items()}
            print(json.dumps(report_json, indent=2))
        else:
            print_report(report)

        # Exit with error code if migration failed
        if report["failed"] > 0:
            sys.exit(1)

    except Exception as e:
        logger.error(f"Script failed: {e}", exc_info=True)
        sys.exit(2)
