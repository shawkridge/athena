#!/usr/bin/env python3
"""Session 5: Extract metadata helper function and apply to handlers"""

import re
from pathlib import Path
from typing import Tuple

# Helper function code to inject
METADATA_HELPER = '''
def _build_handler_metadata(operation: str, schema: str) -> dict:
    """Build standardized handler metadata dict for StructuredResult."""
    return {"operation": operation, "schema": schema}
'''

def extract_and_apply_metadata_helper(filepath: Path) -> Tuple[int, int]:
    """Extract metadata helper and apply to handlers in file.

    Returns: (metadata_dicts_replaced, tokens_saved)
    """
    content = filepath.read_text()
    original_content = content

    # Check if helper already exists
    if "_build_handler_metadata" in content:
        return 0, 0  # Already extracted

    # Find all metadata dict patterns
    pattern = r'metadata=\{"operation":\s*"([^"]+)",\s*"schema":\s*"([^"]+)"\}'
    matches = list(re.finditer(pattern, content))

    if not matches:
        return 0, 0

    # Replace all metadata dicts with helper calls
    def replace_metadata(match):
        operation = match.group(1)
        schema = match.group(2)
        return f'metadata=_build_handler_metadata("{operation}", "{schema}")'

    content = re.sub(pattern, replace_metadata, content)

    # Inject helper function at the top of the PlanningHandlersMixin class or after imports
    # Find where to inject (after imports, before first class/function)
    insertion_point = None

    # Look for the class definition that contains handlers
    class_match = re.search(r'^class \w+.*?:\n', content, re.MULTILINE)
    if class_match:
        insertion_point = class_match.end()

    if insertion_point:
        content = content[:insertion_point] + '\n    ' + METADATA_HELPER.replace('\n', '\n    ') + '\n\n' + content[insertion_point:]

    # Write back
    filepath.write_text(content)

    # Estimate tokens saved
    # Each metadata dict is about 50-70 characters
    # Helper call is about 40-50 characters
    # Plus we add helper function once (~80 chars)
    tokens_before = len(original_content) // 4
    tokens_after = len(content) // 4
    tokens_saved = tokens_before - tokens_after

    return len(matches), tokens_saved

def main():
    """Apply metadata helper across all handler files."""

    files_to_process = [
        'src/athena/mcp/handlers_planning.py',
        'src/athena/mcp/handlers_system.py',
        'src/athena/mcp/handlers_procedural.py',
        'src/athena/mcp/handlers_prospective.py',
        'src/athena/mcp/handlers_episodic.py',
        'src/athena/mcp/handlers_graph.py',
    ]

    total_replaced = 0
    total_tokens_saved = 0

    print("\n" + "="*70)
    print("SESSION 5: METADATA HELPER EXTRACTION")
    print("="*70 + "\n")

    for filepath_str in files_to_process:
        filepath = Path(filepath_str)
        if not filepath.exists():
            print(f"⊘ {filepath_str} not found")
            continue

        replaced, tokens = extract_and_apply_metadata_helper(filepath)
        if replaced > 0:
            total_replaced += replaced
            total_tokens_saved += tokens
            print(f"✅ {filepath.name}: {replaced} metadata dicts replaced (~{tokens} tokens)")
        else:
            print(f"⊘ {filepath.name}: No metadata dicts to replace")

    print("\n" + "="*70)
    print(f"TOTAL METADATA DICTS REPLACED: {total_replaced}")
    print(f"ESTIMATED TOKENS SAVED: ~{total_tokens_saved}")
    print("="*70 + "\n")

    # Verify syntax
    import subprocess
    print("Verifying Python syntax...\n")

    all_valid = True
    for filepath_str in files_to_process:
        filepath = Path(filepath_str)
        if not filepath.exists():
            continue

        result = subprocess.run(
            ["python", "-m", "py_compile", str(filepath)],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print(f"✅ {filepath.name}")
        else:
            print(f"❌ {filepath.name}: {result.stderr[:100]}")
            all_valid = False

    if all_valid:
        print("\n✅ All files compile successfully!")
        return 0
    else:
        print("\n❌ Some files have syntax errors - rolling back")
        # Revert all changes
        import os
        os.system("git checkout -- src/athena/mcp/handlers_*.py")
        return 1

if __name__ == "__main__":
    exit(main())
