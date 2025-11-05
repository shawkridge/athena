#!/usr/bin/env python3
"""
Hook Instrumentation Tool - Automatically add logging to all hooks

This script adds standardized logging to all hook scripts, enabling
execution tracking and performance monitoring.

Usage:
    python3 instrument_hooks.py --dry-run              # Preview changes
    python3 instrument_hooks.py --apply                # Apply changes
    python3 instrument_hooks.py --revert               # Revert changes
"""

import sys
import re
from pathlib import Path
from datetime import datetime
import argparse
import shutil

class HookInstrumenter:
    def __init__(self, hooks_dir):
        self.hooks_dir = Path(hooks_dir)
        self.backup_dir = self.hooks_dir / ".backups"
        self.backup_dir.mkdir(exist_ok=True)

    def get_hook_files(self):
        """Get all hook .sh files (excluding lib and backups)"""
        return sorted([
            f for f in self.hooks_dir.glob("*.sh")
            if f.name != "validate-hooks.sh"
        ])

    def get_hook_name(self, hook_file):
        """Extract hook name from filename"""
        return hook_file.stem

    def extract_header(self, content):
        """Extract the shebang and initial comments"""
        lines = content.split('\n')
        header_lines = []
        i = 0

        # Extract shebang
        if lines[0].startswith('#!'):
            header_lines.append(lines[0])
            i = 1

        # Extract initial comments
        while i < len(lines) and lines[i].startswith('#'):
            header_lines.append(lines[i])
            i += 1

        # Skip blank lines
        while i < len(lines) and not lines[i].strip():
            header_lines.append(lines[i])
            i += 1

        return '\n'.join(header_lines), '\n'.join(lines[i:])

    def should_instrument(self, content):
        """Check if hook already has logging"""
        return 'log_hook_start' not in content

    def instrument_hook(self, hook_file):
        """Add logging to a hook file"""
        hook_name = self.get_hook_name(hook_file)
        content = hook_file.read_text()

        if not self.should_instrument(content):
            return None, "Already instrumented"

        header, body = self.extract_header(content)

        # Create instrumented version
        instrumented = f"""{header}

# ============================================================
# INSTRUMENTATION: Hook Execution Logging
# ============================================================
# Added by instrument_hooks.py on {datetime.now().isoformat()}

source ~/.claude/hooks/lib/hook_logger.sh || exit 1
log_hook_start "{hook_name}"
hook_start_time=$(date +%s%N)

# ============================================================
# HOOK BODY
# ============================================================

{body}

# ============================================================
# INSTRUMENTATION: Log Hook Result
# ============================================================

hook_end_time=$(date +%s%N)
hook_duration_ms=$(( (hook_end_time - hook_start_time) / 1000000 ))

if [ $? -eq 0 ]; then
  log_hook_success "{hook_name}" "$hook_duration_ms" "Hook completed successfully"
else
  log_hook_failure "{hook_name}" "$hook_duration_ms" "Hook exited with error"
fi

exit 0
"""

        return instrumented, "Instrumented successfully"

    def backup_hook(self, hook_file):
        """Create backup of original hook"""
        backup_file = self.backup_dir / f"{hook_file.name}.bak-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(hook_file, backup_file)
        return backup_file

    def apply_instrumentation(self, dry_run=True):
        """Apply instrumentation to all hooks"""
        hook_files = self.get_hook_files()
        results = {
            "instrumented": [],
            "skipped": [],
            "errors": []
        }

        print("=" * 70)
        print("HOOK INSTRUMENTATION")
        print("=" * 70)
        print(f"Dry-run: {dry_run}")
        print(f"Processing {len(hook_files)} hooks...\n")

        for hook_file in hook_files:
            hook_name = self.get_hook_name(hook_file)
            instrumented, msg = self.instrument_hook(hook_file)

            if instrumented is None:
                print(f"⊘ {hook_name:<45} {msg}")
                results["skipped"].append(hook_name)
            else:
                if not dry_run:
                    # Create backup
                    backup_file = self.backup_hook(hook_file)

                    # Write instrumented version
                    hook_file.write_text(instrumented)

                print(f"✓ {hook_name:<45} Instrumented ({len(instrumented)} bytes)")
                results["instrumented"].append(hook_name)

        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Instrumented: {len(results['instrumented'])}")
        print(f"Skipped:      {len(results['skipped'])}")
        print(f"Errors:       {len(results['errors'])}")

        if not dry_run:
            print(f"\nBackups saved to: {self.backup_dir}")
            print("✓ All hooks instrumented with logging")

            print("\nTo view hook statistics, use:")
            print("  source ~/.claude/hooks/lib/hook_logger.sh")
            print("  all_hook_stats")

        return results

    def revert_instrumentation(self):
        """Revert all hooks from backup"""
        if not self.backup_dir.exists():
            print("No backups found")
            return

        backups = sorted(self.backup_dir.glob("*.sh.bak-*"))
        if not backups:
            print("No backups found")
            return

        # Get most recent backups per hook
        most_recent = {}
        for backup in backups:
            hook_name = backup.name.rsplit('.bak-', 1)[0]
            if hook_name not in most_recent or backup.stat().st_mtime > most_recent[hook_name].stat().st_mtime:
                most_recent[hook_name] = backup

        print("=" * 70)
        print("REVERTING INSTRUMENTATION")
        print("=" * 70)

        for original_name, backup_file in most_recent.items():
            original_file = self.hooks_dir / original_name
            if original_file.exists():
                shutil.copy2(backup_file, original_file)
                print(f"✓ Reverted {original_name}")

        print("\n✓ All hooks reverted to original versions")


def main():
    parser = argparse.ArgumentParser(
        description="Instrument hooks with execution logging"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying files"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply instrumentation to all hooks"
    )
    parser.add_argument(
        "--revert",
        action="store_true",
        help="Revert instrumentation from backups"
    )

    args = parser.parse_args()

    hooks_dir = Path.home() / ".claude" / "hooks"

    if not hooks_dir.exists():
        print(f"Error: Hooks directory not found: {hooks_dir}")
        sys.exit(1)

    instrumenter = HookInstrumenter(hooks_dir)

    if args.revert:
        instrumenter.revert_instrumentation()
    elif args.apply:
        instrumenter.apply_instrumentation(dry_run=False)
    else:
        # Default: dry-run
        instrumenter.apply_instrumentation(dry_run=True)


if __name__ == "__main__":
    main()
