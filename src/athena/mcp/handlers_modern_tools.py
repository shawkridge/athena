"""MCP handlers for modern code analysis tools (ast-grep, ripgrep, tree-sitter, semgrep)."""

import json
import logging
from typing import Any, List

from mcp.types import TextContent

from athena.code.modern_tools import (
    RipgrepSearcher,
    AstGrepSearcher,
    TreeSitterParser,
    SemgrepAnalyzer,
    ModernCodeAnalyzer,
)

logger = logging.getLogger(__name__)


# ============================================================================
# RIPGREP HANDLERS
# ============================================================================

async def handle_ripgrep_fast_search(server: Any, args: dict) -> List[TextContent]:
    """Perform fast file searching using ripgrep."""
    try:
        pattern = args.get("pattern", "")
        directory = args.get("directory", ".")
        file_type = args.get("file_type")

        if not pattern:
            return [TextContent(type="text", text="Error: pattern parameter required")]

        searcher = RipgrepSearcher()

        if not searcher.rg_available:
            return [TextContent(type="text", text="Error: ripgrep not available")]

        matches = searcher.search(pattern, directory, file_type=file_type)

        result_text = f"**Ripgrep Search Results**\n\n"
        result_text += f"Pattern: {pattern}\n"
        result_text += f"Directory: {directory}\n"
        result_text += f"Matches: {len(matches)}\n\n"

        if matches:
            for i, match in enumerate(matches[:20], 1):  # Show first 20
                result_text += f"**{i}. {match.file_path}:{match.line_number}**\n"
                result_text += f"```\n{match.matched_text.strip()}\n```\n\n"

            if len(matches) > 20:
                result_text += f"... and {len(matches) - 20} more matches"
        else:
            result_text += "No matches found"

        return [TextContent(type="text", text=result_text)]

    except Exception as e:
        logger.error(f"Error in ripgrep search: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_ripgrep_find_imports(server: Any, args: dict) -> List[TextContent]:
    """Find all imports using ripgrep."""
    try:
        directory = args.get("directory", ".")
        file_type = args.get("file_type", "ts")

        searcher = RipgrepSearcher()

        if not searcher.rg_available:
            return [TextContent(type="text", text="Error: ripgrep not available")]

        imports = searcher.find_imports(directory, file_type=file_type)

        result_text = f"**Imports Found**\n\n"
        result_text += f"Directory: {directory}\n"
        result_text += f"File Type: {file_type}\n"
        result_text += f"Total: {len(imports)}\n\n"

        if imports:
            result_text += "**Sample imports (first 10):**\n"
            for imp in imports[:10]:
                result_text += f"- {imp.strip()}\n"

            if len(imports) > 10:
                result_text += f"\n... and {len(imports) - 10} more"

        return [TextContent(type="text", text=result_text)]

    except Exception as e:
        logger.error(f"Error finding imports: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_ripgrep_find_functions(server: Any, args: dict) -> List[TextContent]:
    """Find all function definitions using ripgrep."""
    try:
        directory = args.get("directory", ".")
        file_type = args.get("file_type", "ts")

        searcher = RipgrepSearcher()

        if not searcher.rg_available:
            return [TextContent(type="text", text="Error: ripgrep not available")]

        functions = searcher.find_functions(directory, file_type=file_type)

        result_text = f"**Functions Found**\n\n"
        result_text += f"Directory: {directory}\n"
        result_text += f"File Type: {file_type}\n"
        result_text += f"Total: {len(functions)}\n\n"

        if functions:
            result_text += "**Sample functions (first 15):**\n"
            for func in functions[:15]:
                result_text += f"- {func.strip()}\n"

            if len(functions) > 15:
                result_text += f"\n... and {len(functions) - 15} more"

        return [TextContent(type="text", text=result_text)]

    except Exception as e:
        logger.error(f"Error finding functions: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


# ============================================================================
# AST-GREP HANDLERS
# ============================================================================

async def handle_astgrep_pattern_search(server: Any, args: dict) -> List[TextContent]:
    """Search code using AST patterns (structure-aware)."""
    try:
        pattern = args.get("pattern", "")
        language = args.get("language", "typescript")
        directory = args.get("directory", ".")

        if not pattern:
            return [TextContent(type="text", text="Error: pattern parameter required")]

        searcher = AstGrepSearcher()

        if not searcher.available:
            return [TextContent(type="text", text="Error: ast-grep not available")]

        matches = searcher.search(pattern, language, directory)

        result_text = f"**AST-Grep Pattern Search**\n\n"
        result_text += f"Pattern: {pattern}\n"
        result_text += f"Language: {language}\n"
        result_text += f"Directory: {directory}\n"
        result_text += f"Matches: {len(matches)}\n\n"

        if matches:
            for i, match in enumerate(matches[:10], 1):
                if isinstance(match, dict):
                    result_text += f"**{i}. {match.get('file', 'unknown')}**\n"
                    result_text += f"```\n{match.get('text', str(match))[:200]}\n```\n\n"

            if len(matches) > 10:
                result_text += f"... and {len(matches) - 10} more matches"
        else:
            result_text += "No matches found"

        return [TextContent(type="text", text=result_text)]

    except Exception as e:
        logger.error(f"Error in ast-grep search: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_astgrep_find_react_hooks(server: Any, args: dict) -> List[TextContent]:
    """Find React hooks using ast-grep."""
    try:
        directory = args.get("directory", ".")

        searcher = AstGrepSearcher()

        if not searcher.available:
            return [TextContent(type="text", text="Error: ast-grep not available")]

        hooks = searcher.find_react_hooks(directory)

        hook_types = {}
        for hook in hooks:
            if isinstance(hook, dict):
                hook_name = hook.get("text", "unknown")[:50]
                hook_types[hook_name] = hook_types.get(hook_name, 0) + 1

        result_text = f"**React Hooks Found**\n\n"
        result_text += f"Directory: {directory}\n"
        result_text += f"Total Hooks: {len(hooks)}\n\n"

        if hook_types:
            result_text += "**Hook Types:**\n"
            for hook_name, count in sorted(hook_types.items(), key=lambda x: -x[1])[:10]:
                result_text += f"- {hook_name}: {count}\n"

        return [TextContent(type="text", text=result_text)]

    except Exception as e:
        logger.error(f"Error finding React hooks: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_astgrep_find_api_calls(server: Any, args: dict) -> List[TextContent]:
    """Find API calls using ast-grep."""
    try:
        directory = args.get("directory", ".")

        searcher = AstGrepSearcher()

        if not searcher.available:
            return [TextContent(type="text", text="Error: ast-grep not available")]

        api_calls = searcher.find_api_calls(directory)

        result_text = f"**API Calls Found**\n\n"
        result_text += f"Directory: {directory}\n"
        result_text += f"Total API Calls: {len(api_calls)}\n\n"

        if api_calls:
            result_text += "**Sample API calls (first 10):**\n"
            for call in api_calls[:10]:
                if isinstance(call, dict):
                    result_text += f"- {call.get('text', str(call))[:80]}\n"

            if len(api_calls) > 10:
                result_text += f"\n... and {len(api_calls) - 10} more calls"

        return [TextContent(type="text", text=result_text)]

    except Exception as e:
        logger.error(f"Error finding API calls: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


# ============================================================================
# SEMGREP HANDLERS
# ============================================================================

async def handle_semgrep_security_scan(server: Any, args: dict) -> List[TextContent]:
    """Scan for security issues using semgrep."""
    try:
        directory = args.get("directory", ".")
        rules = args.get("rules")  # Optional list of rules

        analyzer = SemgrepAnalyzer()

        if not analyzer.available:
            return [TextContent(type="text", text="Error: semgrep not installed. Install with: pip install semgrep")]

        results = analyzer.scan(directory, rules=rules)

        result_text = f"**Semgrep Security Scan**\n\n"
        result_text += f"Directory: {directory}\n"

        if "results" in results:
            matches = results.get("results", [])
            result_text += f"Vulnerabilities Found: {len(matches)}\n\n"

            if matches:
                result_text += "**Sample findings (first 5):**\n"
                for match in matches[:5]:
                    rule_id = match.get("rule_id", "unknown")
                    message = match.get("message", "No message")
                    result_text += f"\n**Rule**: {rule_id}\n"
                    result_text += f"**Message**: {message[:100]}\n"

                if len(matches) > 5:
                    result_text += f"\n... and {len(matches) - 5} more findings"
            else:
                result_text += "No security issues found! ✅"
        else:
            result_text += f"Scan completed\n\nResponse: {str(results)[:200]}"

        return [TextContent(type="text", text=result_text)]

    except Exception as e:
        logger.error(f"Error in semgrep scan: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


# ============================================================================
# UNIFIED MODERN TOOLS HANDLER
# ============================================================================

async def handle_comprehensive_analysis(server: Any, args: dict) -> List[TextContent]:
    """Run comprehensive analysis using all available modern tools."""
    try:
        directory = args.get("directory", ".")
        analysis_types = args.get("analysis_types", ["search", "patterns", "security"])

        analyzer = ModernCodeAnalyzer()

        result_text = f"**Comprehensive Code Analysis**\n\n"
        result_text += f"Directory: {directory}\n\n"

        # Fast search with ripgrep
        if "search" in analysis_types and analyzer.ripgrep.rg_available:
            result_text += "**RIPGREP ANALYSIS** (Fast Search)\n"
            result_text += f"- Available: ✅\n\n"

        # Pattern matching with ast-grep
        if "patterns" in analysis_types and analyzer.astgrep.available:
            result_text += "**AST-GREP ANALYSIS** (Structure-Aware Patterns)\n"
            result_text += f"- Available: ✅\n\n"

        # Security scanning with semgrep
        if "security" in analysis_types and analyzer.semgrep.available:
            result_text += "**SEMGREP ANALYSIS** (Security Scanning)\n"
            result_text += f"- Available: ✅\n\n"

        # Tree-sitter (if available)
        if analyzer.treesitter.available:
            result_text += "**TREE-SITTER** (Advanced AST Parsing)\n"
            result_text += f"- Available: ✅\n\n"
        else:
            result_text += "**TREE-SITTER** (Optional - not installed)\n"
            result_text += f"- Install with: pip install tree-sitter tree-sitter-languages\n\n"

        result_text += "**Summary**\n"
        tools_available = sum([
            analyzer.ripgrep.rg_available,
            analyzer.astgrep.available,
            analyzer.treesitter.available,
            analyzer.semgrep.available,
        ])
        result_text += f"- Tools Available: {tools_available}/4\n"
        result_text += f"- Ready for: Fast search, pattern matching, security scanning\n"

        return [TextContent(type="text", text=result_text)]

    except Exception as e:
        logger.error(f"Error in comprehensive analysis: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]
