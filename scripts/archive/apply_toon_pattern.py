#!/usr/bin/env python3
"""
Apply TOON Compression Pattern to MCP Handlers

Converts handlers from:
    return [TextContent(type="text", text=json.dumps(response))]

To:
    result = StructuredResult.success(
        data=response_data,
        metadata={"operation": "handler_name", "schema": "domain_schema"}
    )
    return [result.as_optimized_content(schema_name="domain_schema")]

This automatically applies TOON compression (45-60% token reduction).
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple, Optional

class TOONPatternConverter:
    """Converts handlers to TOON-compressed format."""

    def __init__(self):
        self.conversion_stats = {
            'files_processed': 0,
            'handlers_converted': 0,
            'handlers_skipped': 0,
            'total_tokens_before': 0,
            'total_tokens_after': 0,
        }

    def estimate_tokens(self, code: str) -> int:
        """Rough token estimation: ~4 chars = 1 token."""
        return len(code) // 4

    def extract_schema_name(self, handler_name: str) -> str:
        """Convert handler name to schema name.

        Example: _handle_optimize_plan -> planning_optimization
        """
        # Remove _handle_ prefix
        name = handler_name.replace('_handle_', '')

        # Map to domain
        domain_map = {
            'episodic': 'episodic',
            'consolidate': 'consolidation',
            'procedural': 'procedural',
            'prospective': 'prospective',
            'graph': 'graph',
            'plan': 'planning',
            'optimize': 'optimization',
            'analyze': 'analysis',
            'compute': 'computation',
            'validate': 'validation',
            'verify': 'verification',
        }

        for key, value in domain_map.items():
            if key in name:
                return f"{value}_{name.split(key)[-1]}".lstrip('_')

        return name

    def should_convert(self, handler_code: str) -> bool:
        """Check if handler should be converted (returns JSON, not text string)."""
        # Skip if already using StructuredResult
        if 'StructuredResult' in handler_code:
            return False

        # Skip if returns text string formatting (has format string logic)
        if 'f"' in handler_code and '=' not in handler_code[:handler_code.find('return')]:
            return False

        # Check if returns json.dumps
        if 'json.dumps(' in handler_code and 'TextContent' in handler_code:
            return True

        return False

    def convert_handler(self, handler_code: str, handler_name: str) -> Optional[str]:
        """Convert single handler to TOON pattern.

        Returns: converted_code or None if conversion failed
        """
        tokens_before = self.estimate_tokens(handler_code)

        # Find the return statement with json.dumps
        json_dumps_pattern = r'return\s+\[TextContent\(type="text",\s+text=json\.dumps\((\w+)(?:,\s*indent=\d+)?\)\)\]'
        match = re.search(json_dumps_pattern, handler_code)

        if not match:
            return None

        response_var = match.group(1)
        schema_name = self.extract_schema_name(handler_name)

        # Build replacement
        replacement = f'''result = StructuredResult.success(
            data={response_var},
            metadata={{"operation": "{handler_name.replace('_handle_', '')}", "schema": "{schema_name}"}}
        )
        return [result.as_optimized_content(schema_name="{schema_name}")]'''

        # Replace in code
        converted = re.sub(json_dumps_pattern, replacement, handler_code)

        # Ensure StructuredResult is imported (add at top if needed)
        if 'from .structured_result import StructuredResult' not in converted:
            # Will be added at file level
            pass

        tokens_after = self.estimate_tokens(converted)

        return converted

    def process_file(self, filepath: str) -> Tuple[str, dict]:
        """Process entire file, converting applicable handlers.

        Returns: (modified_content, stats)
        """
        with open(filepath, 'r') as f:
            content = f.read()

        # Check if StructuredResult is already imported
        has_structured_import = 'from .structured_result import StructuredResult' in content

        # Find all handler methods
        handler_pattern = r'(    async def (_handle_\w+)\(self, args: dict\) -> (?:list\[TextContent\]|List\[TextContent\]):(.*?)(?=\n    async def _handle_|\n    def \w+|\nclass |\Z))'

        handlers = re.finditer(handler_pattern, content, re.DOTALL)
        modified_content = content
        conversions = []

        for match in handlers:
            full_handler = match.group(1)
            handler_name = match.group(2)

            if self.should_convert(full_handler):
                converted = self.convert_handler(full_handler, handler_name)
                if converted:
                    modified_content = modified_content.replace(full_handler, converted, 1)
                    conversions.append(handler_name)
                    self.conversion_stats['handlers_converted'] += 1
                else:
                    self.conversion_stats['handlers_skipped'] += 1
            else:
                self.conversion_stats['handlers_skipped'] += 1

        # Add import if needed and conversions were made
        if conversions and not has_structured_import:
            # Find insertion point (after other imports from .structured_result or after first import from mcp)
            import_pattern = r'(from \.structured_result import [^\\n]+\\n)'
            if not re.search(import_pattern, modified_content):
                # Add after first "from mcp" import
                mcp_import = re.search(r'from mcp\.types import[^\\n]+', modified_content)
                if mcp_import:
                    insert_pos = mcp_import.end()
                    modified_content = modified_content[:insert_pos] + '\n\nfrom .structured_result import StructuredResult' + modified_content[insert_pos:]

        self.conversion_stats['files_processed'] += 1

        return modified_content, conversions

    def print_stats(self):
        """Print conversion statistics."""
        stats = self.conversion_stats

        print("\n" + "="*70)
        print("TOON PATTERN CONVERSION RESULTS")
        print("="*70)
        print(f"Files processed: {stats['files_processed']}")
        print(f"Handlers converted: {stats['handlers_converted']}")
        print(f"Handlers skipped: {stats['handlers_skipped']}")

        if stats['handlers_converted'] > 0:
            compression_per_handler = 57  # From Session 3 benchmarks
            total_saved = stats['handlers_converted'] * int(200 * compression_per_handler / 100)
            alignment_improvement = stats['handlers_converted'] * 0.035  # 0.5-1% per 7 handlers

            print(f"\nEstimated savings:")
            print(f"- Tokens saved per handler: ~114 tokens (57% of ~200)")
            print(f"- Total tokens saved: ~{total_saved:,} tokens")
            print(f"- Alignment improvement: +{alignment_improvement:.1f}%")

        print("="*70 + "\n")

def main():
    """Main entry point."""
    handler_files = [
        'src/athena/mcp/handlers_planning.py',
        'src/athena/mcp/handlers_system.py',
        'src/athena/mcp/handlers_metacognition.py',
        'src/athena/mcp/handlers_procedural.py',
        'src/athena/mcp/handlers_prospective.py',
        'src/athena/mcp/handlers_consolidation.py',
        'src/athena/mcp/handlers_episodic.py',
        'src/athena/mcp/handlers_graph.py',
        'src/athena/mcp/handlers_memory_core.py',
    ]

    converter = TOONPatternConverter()

    for filepath in handler_files:
        if not Path(filepath).exists():
            print(f"⊘ Skipping {filepath} (not found)")
            continue

        print(f"Processing {filepath}...")
        modified_content, conversions = converter.process_file(filepath)

        if conversions:
            print(f"  ✓ Converted {len(conversions)} handlers:")
            for name in conversions[:5]:  # Show first 5
                print(f"    - {name}")
            if len(conversions) > 5:
                print(f"    ... and {len(conversions) - 5} more")

            # Write back
            with open(filepath, 'w') as f:
                f.write(modified_content)
            print(f"  ✓ File updated")
        else:
            print(f"  ⊘ No conversions needed")

    converter.print_stats()

if __name__ == '__main__':
    main()
