#!/usr/bin/env python3
"""Session 5: Extract common patterns and create helper functions"""

import re
from pathlib import Path
from typing import Tuple

def analyze_handlers_for_patterns(filepath: Path) -> dict:
    """Analyze handlers to identify common patterns."""

    content = filepath.read_text()
    patterns = {
        'error_response_json_dumps': 0,
        'try_except_error_handling': 0,
        'structured_result_success': 0,
        'structured_result_error': 0,
        'metadata_dicts': 0,
    }

    # Count error handling patterns
    patterns['error_response_json_dumps'] = len(re.findall(
        r'error_response\s*=\s*json\.dumps',
        content
    ))

    patterns['try_except_error_handling'] = len(re.findall(
        r'except\s+Exception\s+as\s+e:',
        content
    ))

    patterns['structured_result_success'] = len(re.findall(
        r'StructuredResult\.success\(',
        content
    ))

    patterns['structured_result_error'] = len(re.findall(
        r'StructuredResult\.error\(',
        content
    ))

    patterns['metadata_dicts'] = len(re.findall(
        r'metadata=\{"operation":\s*"[^"]+",\s*"schema":\s*"[^"]+"\}',
        content
    ))

    return patterns

def main():
    """Analyze all handler files for patterns."""

    files_to_analyze = [
        'src/athena/mcp/handlers_planning.py',
        'src/athena/mcp/handlers_system.py',
        'src/athena/mcp/handlers_procedural.py',
        'src/athena/mcp/handlers_prospective.py',
        'src/athena/mcp/handlers_episodic.py',
        'src/athena/mcp/handlers_graph.py',
    ]

    print("\n" + "="*70)
    print("SESSION 5: PATTERN ANALYSIS")
    print("="*70 + "\n")

    total_patterns = {
        'error_response_json_dumps': 0,
        'try_except_error_handling': 0,
        'structured_result_success': 0,
        'structured_result_error': 0,
        'metadata_dicts': 0,
    }

    for filepath_str in files_to_analyze:
        filepath = Path(filepath_str)
        if not filepath.exists():
            continue

        patterns = analyze_handlers_for_patterns(filepath)
        print(f"{filepath.name}:")
        for pattern_name, count in patterns.items():
            if count > 0:
                print(f"  {pattern_name}: {count}")
            total_patterns[pattern_name] += count
        print()

    print("="*70)
    print("TOTAL PATTERN OCCURRENCES:")
    print("="*70)
    for pattern_name, count in total_patterns.items():
        print(f"  {pattern_name}: {count}")

    print("\n" + "="*70)
    print("OPTIMIZATION OPPORTUNITIES:")
    print("="*70)
    print(f"1. Error handling consolidation: {total_patterns['error_response_json_dumps']} duplicates")
    print(f"2. Try/except standardization: {total_patterns['try_except_error_handling']} blocks")
    print(f"3. Metadata helper function: {total_patterns['metadata_dicts']} metadata dicts")
    print(f"4. StructuredResult usage: {total_patterns['structured_result_success'] + total_patterns['structured_result_error']} calls")

    print("\n" + "="*70)
    print("RECOMMENDATIONS FOR SESSION 5:")
    print("="*70)
    print("✅ Focus on metadata helper function (192 calls)")
    print("   - Extract to: _build_handler_metadata(operation, schema)")
    print("   - Estimated savings: 500-1000 tokens")
    print("\n✅ Standardize error responses")
    print("   - Use helper: _error_response(error, details)")
    print("   - Estimated savings: 300-500 tokens")
    print("\n⚠️ Docstrings already mostly single-line")
    print("   - Docstring compression = low priority (skip)")
    print("\n✅ High-value targets: Pattern extraction helpers")
    print("   - Build 3-5 helper functions")
    print("   - Estimated savings: 1000-2000 tokens")
    print("   - Time: 2-3 hours")

if __name__ == "__main__":
    main()
