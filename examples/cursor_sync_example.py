#!/usr/bin/env python3
"""Example: Incremental Event Sync with Cursor Management

This example demonstrates how to use the cursor management system for
incremental event synchronization from external sources.

Scenario: Sync file changes from a project directory

Run:
    python examples/cursor_sync_example.py
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from athena.core.database import Database
from athena.episodic.cursor import CursorManager, FileSystemCursor
from athena.episodic.store import EpisodicStore
from athena.episodic.models import EpisodicEvent, EventType, EventContext, EventOutcome


class FileSystemSyncExample:
    """Example: Sync file changes using cursors for incremental sync."""

    def __init__(self, db_path: str, project_path: str, project_id: int = 1):
        self.db = Database(db_path)
        self.cursor_mgr = CursorManager(self.db)
        self.episodic_store = EpisodicStore(self.db)
        self.project_path = Path(project_path)
        self.project_id = project_id
        self.source_id = f"filesystem:{self.project_path}"

    def sync_events(self) -> dict:
        """Sync file change events (full or incremental based on cursor).

        Returns:
            Sync statistics dict
        """
        print(f"\n{'='*60}")
        print(f"Syncing events from: {self.project_path}")
        print(f"Source ID: {self.source_id}")
        print(f"{'='*60}\n")

        # Load cursor from previous sync
        cursor_data = self.cursor_mgr.get_cursor(self.source_id)

        if cursor_data is None:
            print("✨ No cursor found - performing FULL SYNC")
            stats = self._full_sync()
        else:
            print("📈 Cursor found - performing INCREMENTAL SYNC")
            cursor = FileSystemCursor.from_dict(cursor_data)
            print(f"   Last scan: {cursor.last_scan_time}")
            print(f"   Tracked files: {len(cursor.processed_files)}")
            stats = self._incremental_sync(cursor)

        # Save cursor after sync
        new_cursor = self._create_cursor()
        self.cursor_mgr.update_cursor(self.source_id, new_cursor.to_dict())
        print(f"\n✅ Cursor saved - {len(new_cursor.processed_files)} files tracked")

        return stats

    def _full_sync(self) -> dict:
        """Full sync: Process all Python files in directory."""
        print("\n📁 Scanning all files...\n")

        files_found = list(self.project_path.rglob("*.py"))
        events_created = 0

        for file_path in files_found:
            event = self._create_event(file_path, "file_added")
            event_id = self.episodic_store.record_event(event)

            print(f"   ➕ Added: {file_path.name} (event_id={event_id})")
            events_created += 1

        return {
            "sync_type": "full",
            "files_scanned": len(files_found),
            "events_created": events_created,
        }

    def _incremental_sync(self, cursor: FileSystemCursor) -> dict:
        """Incremental sync: Process only new/modified files since cursor."""
        print("\n📁 Scanning for changes...\n")

        files_scanned = 0
        events_created = 0
        new_files = 0
        modified_files = 0

        for file_path in self.project_path.rglob("*.py"):
            files_scanned += 1
            path_str = str(file_path)
            current_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)

            if path_str not in cursor.processed_files:
                # New file since last sync
                event = self._create_event(file_path, "file_added")
                event_id = self.episodic_store.record_event(event)

                print(f"   ➕ New: {file_path.name} (event_id={event_id})")
                events_created += 1
                new_files += 1

            elif cursor.processed_files[path_str] < current_mtime:
                # File modified since last sync
                event = self._create_event(file_path, "file_modified")
                event_id = self.episodic_store.record_event(event)

                print(f"   ✏️  Modified: {file_path.name} (event_id={event_id})")
                events_created += 1
                modified_files += 1

        # Check for deleted files
        deleted_files = 0
        for tracked_path in cursor.processed_files.keys():
            if not Path(tracked_path).exists():
                event = self._create_deleted_event(tracked_path)
                event_id = self.episodic_store.record_event(event)

                print(f"   ❌ Deleted: {Path(tracked_path).name} (event_id={event_id})")
                events_created += 1
                deleted_files += 1

        if events_created == 0:
            print("   ℹ️  No changes detected")

        return {
            "sync_type": "incremental",
            "files_scanned": files_scanned,
            "events_created": events_created,
            "new_files": new_files,
            "modified_files": modified_files,
            "deleted_files": deleted_files,
        }

    def _create_event(self, file_path: Path, change_type: str) -> EpisodicEvent:
        """Create episodic event for file change."""
        return EpisodicEvent(
            project_id=self.project_id,
            session_id="file_sync_session",
            timestamp=datetime.now(),
            event_type=EventType.FILE_CHANGE,
            content=f"{change_type.replace('_', ' ').title()}: {file_path.name}",
            outcome=EventOutcome.SUCCESS,
            context=EventContext(
                cwd=str(self.project_path),
                files=[str(file_path)],
                task="file_sync",
            ),
            file_path=str(file_path),
            language="python" if file_path.suffix == ".py" else None,
        )

    def _create_deleted_event(self, file_path: str) -> EpisodicEvent:
        """Create episodic event for deleted file."""
        return EpisodicEvent(
            project_id=self.project_id,
            session_id="file_sync_session",
            timestamp=datetime.now(),
            event_type=EventType.FILE_CHANGE,
            content=f"File Deleted: {Path(file_path).name}",
            outcome=EventOutcome.SUCCESS,
            context=EventContext(
                cwd=str(self.project_path),
                files=[file_path],
                task="file_sync",
            ),
            file_path=file_path,
        )

    def _create_cursor(self) -> FileSystemCursor:
        """Create cursor with current file modification times."""
        processed_files = {}

        for file_path in self.project_path.rglob("*.py"):
            path_str = str(file_path)
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            processed_files[path_str] = mtime

        return FileSystemCursor(
            last_scan_time=datetime.now(),
            processed_files=processed_files,
        )

    def show_cursor_status(self):
        """Display cursor status for this source."""
        print(f"\n{'='*60}")
        print(f"Cursor Status: {self.source_id}")
        print(f"{'='*60}\n")

        cursor_data = self.cursor_mgr.get_cursor(self.source_id)

        if cursor_data is None:
            print("❌ No cursor found - next sync will be FULL SYNC")
        else:
            cursor = FileSystemCursor.from_dict(cursor_data)
            print(f"✅ Cursor found:")
            print(f"   Last scan: {cursor.last_scan_time}")
            print(f"   Tracked files: {len(cursor.processed_files)}")

            if cursor.processed_files:
                print(f"\n   Recently tracked files:")
                for path, mtime in list(cursor.processed_files.items())[:5]:
                    print(f"      • {Path(path).name} (modified: {mtime})")

                if len(cursor.processed_files) > 5:
                    print(f"      ... and {len(cursor.processed_files) - 5} more")

    def reset_cursor(self):
        """Reset cursor to force full sync on next run."""
        print(f"\n{'='*60}")
        print(f"Resetting Cursor: {self.source_id}")
        print(f"{'='*60}\n")

        deleted = self.cursor_mgr.delete_cursor(self.source_id)

        if deleted:
            print("✅ Cursor deleted - next sync will be FULL SYNC")
        else:
            print("❌ No cursor to delete")

    def list_all_cursors(self):
        """List all cursors in database."""
        print(f"\n{'='*60}")
        print("All Event Source Cursors")
        print(f"{'='*60}\n")

        all_cursors = self.cursor_mgr.list_cursors()

        if not all_cursors:
            print("❌ No cursors found")
        else:
            for i, cursor_info in enumerate(all_cursors, 1):
                print(f"{i}. {cursor_info['source_id']}")
                print(f"   Updated: {cursor_info['updated_at']}")
                print(f"   Data: {len(str(cursor_info['cursor_data']))} bytes")
                print()


def main():
    """Run file sync example."""
    # Configuration
    db_path = "example_memory.db"
    project_path = Path(__file__).parent.parent / "src" / "athena"  # Sync athena source

    # Initialize
    syncer = FileSystemSyncExample(db_path, str(project_path))

    print("\n" + "="*60)
    print("File Sync Example - Cursor Management Demo")
    print("="*60)

    # Show current cursor status
    syncer.show_cursor_status()

    # Perform sync (full or incremental based on cursor)
    stats = syncer.sync_events()

    # Display statistics
    print(f"\n{'='*60}")
    print("Sync Statistics")
    print(f"{'='*60}\n")
    for key, value in stats.items():
        print(f"   {key.replace('_', ' ').title()}: {value}")

    # Show updated cursor status
    syncer.show_cursor_status()

    # List all cursors
    syncer.list_all_cursors()

    print("\n" + "="*60)
    print("Example completed successfully!")
    print("="*60)
    print(f"\nDatabase: {db_path}")
    print("\nTry running again to see incremental sync in action!")
    print("Or modify a file in src/athena/ and re-run.")
    print("\nTo reset and force full sync:")
    print(f"  python {__file__} --reset")
    print("="*60 + "\n")


def reset_mode():
    """Reset cursor to force full sync."""
    db_path = "example_memory.db"
    project_path = Path(__file__).parent.parent / "src" / "athena"

    syncer = FileSystemSyncExample(db_path, str(project_path))
    syncer.reset_cursor()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        reset_mode()
    else:
        main()
