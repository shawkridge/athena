#!/usr/bin/env python3
"""Batch 2 TOON compression conversion for handlers_planning.py"""

import re
from pathlib import Path

def convert_toon_batch2():
    """Convert 8 more handlers to TOON pattern."""

    filepath = Path("src/athena/mcp/handlers_planning.py")
    content = filepath.read_text()

    conversions = []

    # Handler specifications with exact patterns to replace
    handlers = [
        {
            "name": "_handle_verify_plan",
            "success_var": "response_data",
            "schema": "planning_verification",
        },
        {
            "name": "_handle_planning_validation_benchmark",
            "success_var": "response_data",
            "schema": "validation_benchmark",
        },
        {
            "name": "_handle_research_task",
            "success_var": "response_data",
            "error_var": "error_response",
            "schema": "research_task",
        },
        {
            "name": "_handle_research_findings",
            "success_var": "response_data",
            "error_var": "error_response",
            "schema": "research_findings",
        },
        {
            "name": "_handle_analyze_estimation_accuracy",
            "success_var": "response_data",
            "schema": "estimation_accuracy",
        },
        {
            "name": "_handle_discover_patterns",
            "success_var": "response_data",
            "schema": "pattern_discovery",
        },
        {
            "name": "_handle_estimate_resources",
            "success_var": "response_data",
            "schema": "resource_estimation",
        },
        {
            "name": "_handle_add_project_dependency",
            "success_var": "response_data",
            "schema": "project_dependency",
        }
    ]

    for handler_spec in handlers:
        success_var = handler_spec["success_var"]
        schema_name = handler_spec["schema"]

        # Find and replace success returns
        success_pattern = rf'( *)return \[TextContent\(type="text", text=json\.dumps\({success_var}, indent=2\)\)\]'

        def success_repl(match):
            indent = match.group(1)
            return f'''{indent}result = StructuredResult.success(
{indent}    data={success_var},
{indent}    metadata={{"operation": "{handler_spec['name'].replace('_handle_', '')}", "schema": "{schema_name}"}}
{indent})
{indent}return [result.as_optimized_content(schema_name="{schema_name}")]'''

        original = content
        content = re.sub(success_pattern, success_repl, content, count=1)
        if content != original:
            conversions.append(f"✅ {handler_spec['name']} (success)")

        # Replace error returns if specified
        if "error_var" in handler_spec:
            error_var = handler_spec["error_var"]
            error_pattern = rf'( *)return \[TextContent\(type="text", text=json\.dumps\({error_var}, indent=2\)\)\]'

            def error_repl(match):
                indent = match.group(1)
                return f'''{indent}result = StructuredResult.error(
{indent}    details={error_var},
{indent}    metadata={{"operation": "{handler_spec['name'].replace('_handle_', '')}", "schema": "{schema_name}_error"}}
{indent})
{indent}return [result.as_optimized_content(schema_name="{schema_name}_error")]'''

            original = content
            content = re.sub(error_pattern, error_repl, content, count=1)
            if content != original:
                conversions.append(f"✅ {handler_spec['name']} (error)")

    # Write back
    filepath.write_text(content)

    print("\n" + "="*70)
    print(f"TOON CONVERSIONS APPLIED ({len(conversions)})")
    print("="*70)
    for conv in conversions:
        print(f"  {conv}")
    print("="*70)

    # Verify syntax
    import subprocess
    result = subprocess.run(
        ["python", "-m", "py_compile", str(filepath)],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print("✅ Syntax verification passed!")
        return True
    else:
        print(f"❌ Syntax error: {result.stderr}")
        return False

if __name__ == "__main__":
    success = convert_toon_batch2()
    exit(0 if success else 1)
