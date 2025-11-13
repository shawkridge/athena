#!/usr/bin/env python3
"""Session 5: Compress multi-line docstrings to single-line format"""

import re
from pathlib import Path
from typing import Tuple, List

def compress_docstrings(filepath: Path) -> Tuple[int, int]:
    """Compress multi-line docstrings to single-line format.

    Returns: (handlers_modified, tokens_saved)
    """
    content = filepath.read_text()
    original_content = content
    handlers_modified = 0

    # Pattern: async def _handle_xxx ... """..."""
    # Match multi-line docstrings (with newlines inside)
    pattern = r'(async def _handle_\w+\([^)]*\)[^:]*:)\s*"""([^"]*(?:\n[^"]*)*?)"""'

    def replace_docstring(match):
        nonlocal handlers_modified
        sig = match.group(1)
        docstring = match.group(2).strip()

        # Extract first line or first sentence
        first_line = docstring.split('\n')[0].strip()
        if not first_line:
            first_line = docstring.split('.')[0].strip()

        # Shorten to reasonable length
        if len(first_line) > 70:
            first_line = first_line[:67] + "..."

        # Create compressed version: → Description (arrow indicates reference)
        compressed = f'{sig}\n    """→ {first_line}"""'
        handlers_modified += 1
        return compressed

    content = re.sub(pattern, replace_docstring, content, flags=re.MULTILINE)

    # Estimate tokens saved
    tokens_before = len(original_content) // 4
    tokens_after = len(content) // 4
    tokens_saved = tokens_before - tokens_after

    # Write back
    filepath.write_text(content)

    return handlers_modified, tokens_saved

def main():
    """Compress docstrings across all handler files."""

    files_to_process = [
        'src/athena/mcp/handlers_planning.py',
        'src/athena/mcp/handlers_system.py',
        'src/athena/mcp/handlers_procedural.py',
        'src/athena/mcp/handlers_prospective.py',
        'src/athena/mcp/handlers_episodic.py',
        'src/athena/mcp/handlers_graph.py',
    ]

    total_modified = 0
    total_tokens_saved = 0

    print("\n" + "="*70)
    print("SESSION 5: DOCSTRING COMPRESSION")
    print("="*70 + "\n")

    for filepath_str in files_to_process:
        filepath = Path(filepath_str)
        if not filepath.exists():
            print(f"⊘ {filepath_str} not found")
            continue

        modified, tokens = compress_docstrings(filepath)
        if modified > 0:
            total_modified += modified
            total_tokens_saved += tokens
            print(f"✅ {filepath.name}: {modified} docstrings compressed (~{tokens} tokens)")

    print("\n" + "="*70)
    print(f"TOTAL DOCSTRINGS COMPRESSED: {total_modified}")
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
    else:
        print("\n❌ Some files have syntax errors")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
