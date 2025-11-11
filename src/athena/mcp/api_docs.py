"""API documentation generator for MemoryAPI.

Generates human-readable documentation from APISpecification objects,
supporting multiple formats (Markdown, HTML, JSON).

Usage:
    from athena.mcp.api_registry import APIRegistry
    from athena.mcp.api_docs import APIDocumentationGenerator

    registry = APIRegistry.create()
    generator = APIDocumentationGenerator(registry)

    # Generate markdown docs
    docs = generator.generate_markdown()
    print(docs)

    # Generate HTML
    html = generator.generate_html()

    # Generate JSON
    json_data = generator.generate_json()
"""

import json
import logging
from typing import Dict, Any, List
from datetime import datetime
from .api_registry import APIRegistry, APICategory, APISecurityLevel

logger = logging.getLogger(__name__)


class APIDocumentationGenerator:
    """Generate documentation from API registry."""

    def __init__(self, registry: APIRegistry):
        """Initialize documentation generator.

        Args:
            registry: APIRegistry to document
        """
        self.registry = registry

    def generate_markdown(self) -> str:
        """Generate Markdown documentation.

        Returns:
            Markdown-formatted API documentation
        """
        lines = []

        # Header
        lines.append("# MemoryAPI Documentation\n")
        lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")

        # Table of contents
        lines.append("## Table of Contents\n")
        for category in self.registry.get_categories():
            lines.append(f"- [{category.value.title()}](#{category.value})")
        lines.append("")

        # Quick start
        lines.append("## Quick Start\n")
        lines.append("```python")
        lines.append("from athena.mcp.memory_api import MemoryAPI\n")
        lines.append("# Create API instance")
        lines.append("api = MemoryAPI.create()\n")
        lines.append("# Store memory")
        lines.append('memory_id = api.remember("Important finding")\n')
        lines.append("# Recall memory")
        lines.append('results = api.recall("recent findings", limit=5)\n')
        lines.append("# Store event")
        lines.append('event_id = api.remember_event("action", "Ran tests", outcome="success")')
        lines.append("```\n")

        # APIs by category
        for category in self.registry.get_categories():
            lines.append(f"## {category.value.title()}\n")

            apis = self.registry.discover_apis(category=category)

            for api in apis:
                # API heading
                lines.append(f"### {api.name}\n")

                # Description
                lines.append(f"{api.description}\n")

                # Metadata
                metadata = []
                if api.deprecated:
                    metadata.append("⚠️ **Deprecated**")
                metadata.append(f"**Security**: {api.security_level.value}")
                metadata.append(f"**Since**: v{api.since_version}")
                if metadata:
                    lines.append(" | ".join(metadata) + "\n")

                # Parameters
                if api.parameters:
                    lines.append("#### Parameters\n")
                    lines.append("| Name | Type | Required | Default | Description |")
                    lines.append("|------|------|----------|---------|-------------|")

                    for param in api.parameters:
                        default_str = str(param.default) if param.default is not None else "-"
                        required_str = "Yes" if param.required else "No"
                        lines.append(
                            f"| `{param.name}` | `{param.type_name}` | {required_str} | {default_str} | {param.description} |"
                        )
                    lines.append("")

                    # Parameter options
                    for param in api.parameters:
                        if param.options:
                            lines.append(f"**{param.name} options**: {', '.join(param.options)}\n")

                # Return value
                lines.append("#### Returns\n")
                lines.append(f"- **Type**: `{api.return_type}`")
                lines.append(f"- **Description**: {api.return_description}\n")

                # Tags
                if api.tags:
                    lines.append(f"**Tags**: {', '.join(api.tags)}\n")

                # Examples
                if api.examples:
                    lines.append("#### Examples\n")
                    for example in api.examples:
                        lines.append("```python")
                        lines.append(example)
                        lines.append("```")
                    lines.append("")

                lines.append("")

        # Footer
        lines.append("---\n")
        lines.append("## API Usage Tips\n")
        lines.append(
            "1. **Always handle exceptions**: Memory operations can fail due to database issues"
        )
        lines.append("2. **Use appropriate memory types**: Choose the right layer for your data")
        lines.append("3. **Consolidate periodically**: Run consolidation to extract patterns")
        lines.append("4. **Check health regularly**: Use health_check() to monitor system status\n")

        lines.append("## Best Practices\n")
        lines.append("- Use tags to organize memories for easier recall")
        lines.append("- Store context information with events for better temporal reasoning")
        lines.append("- Consolidate after significant work sessions")
        lines.append("- Use prospective memory for planning and scheduling")
        lines.append("- Build knowledge graphs for complex relationships\n")

        return "\n".join(lines)

    def generate_html(self) -> str:
        """Generate HTML documentation.

        Returns:
            HTML-formatted API documentation
        """
        lines = []

        # HTML header
        lines.append("<!DOCTYPE html>")
        lines.append("<html>")
        lines.append("<head>")
        lines.append("<meta charset='utf-8'>")
        lines.append("<meta name='viewport' content='width=device-width, initial-scale=1.0'>")
        lines.append("<title>MemoryAPI Documentation</title>")

        # CSS styles
        lines.append("<style>")
        lines.append("body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }")
        lines.append("h1 { color: #333; border-bottom: 3px solid #007bff; padding-bottom: 10px; }")
        lines.append("h2 { color: #0056b3; margin-top: 40px; }")
        lines.append("h3 { color: #0056b3; margin-top: 30px; }")
        lines.append(".api { background: #f8f9fa; border-left: 4px solid #007bff; padding: 15px; margin: 15px 0; }")
        lines.append(".parameter { background: #fff; border: 1px solid #dee2e6; border-radius: 4px; padding: 10px; margin: 5px 0; }")
        lines.append(".example { background: #f5f5f5; border: 1px solid #ddd; border-radius: 4px; padding: 10px; margin: 10px 0; font-family: monospace; overflow-x: auto; }")
        lines.append("table { border-collapse: collapse; width: 100%; margin: 15px 0; }")
        lines.append("th, td { border: 1px solid #dee2e6; padding: 10px; text-align: left; }")
        lines.append("th { background: #f8f9fa; }")
        lines.append(".metadata { font-size: 0.9em; color: #666; margin: 10px 0; }")
        lines.append(".tags { display: flex; flex-wrap: wrap; gap: 5px; margin: 10px 0; }")
        lines.append(".tag { background: #e9ecef; border-radius: 12px; padding: 2px 10px; font-size: 0.85em; }")
        lines.append(".toc { background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px; padding: 20px; margin: 20px 0; }")
        lines.append(".toc ul { list-style: none; padding-left: 0; }")
        lines.append(".toc li { margin: 5px 0; }")
        lines.append(".toc a { color: #007bff; text-decoration: none; }")
        lines.append(".toc a:hover { text-decoration: underline; }")
        lines.append("</style>")
        lines.append("</head>")
        lines.append("<body>")

        # Title
        lines.append(f"<h1>MemoryAPI Documentation</h1>")
        lines.append(f"<p><em>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</em></p>")

        # Table of contents
        lines.append("<div class='toc'>")
        lines.append("<h2>Table of Contents</h2>")
        lines.append("<ul>")
        for category in self.registry.get_categories():
            lines.append(f"<li><a href='#{category.value}'>{category.value.title()}</a></li>")
        lines.append("</ul>")
        lines.append("</div>")

        # Quick start
        lines.append("<h2>Quick Start</h2>")
        lines.append("<pre class='example'>")
        lines.append("from athena.mcp.memory_api import MemoryAPI\n")
        lines.append("# Create API instance\n")
        lines.append("api = MemoryAPI.create()\n")
        lines.append("# Store memory\n")
        lines.append('memory_id = api.remember("Important finding")\n')
        lines.append("# Recall memory\n")
        lines.append('results = api.recall("recent findings", limit=5)\n')
        lines.append("# Store event\n")
        lines.append('event_id = api.remember_event("action", "Ran tests", outcome="success")')
        lines.append("</pre>")

        # APIs by category
        for category in self.registry.get_categories():
            lines.append(f"<h2 id='{category.value}'>{category.value.title()}</h2>")

            apis = self.registry.discover_apis(category=category)

            for api in apis:
                lines.append(f"<div class='api'>")

                # API heading
                lines.append(f"<h3>{api.name}</h3>")

                # Description
                lines.append(f"<p>{api.description}</p>")

                # Metadata
                lines.append("<div class='metadata'>")
                if api.deprecated:
                    lines.append("<strong>⚠️ Deprecated</strong> | ")
                lines.append(f"<strong>Security:</strong> {api.security_level.value} | ")
                lines.append(f"<strong>Since:</strong> v{api.since_version}")
                lines.append("</div>")

                # Parameters
                if api.parameters:
                    lines.append("<h4>Parameters</h4>")
                    lines.append("<table>")
                    lines.append(
                        "<tr><th>Name</th><th>Type</th><th>Required</th><th>Default</th><th>Description</th></tr>"
                    )

                    for param in api.parameters:
                        default_str = str(param.default) if param.default is not None else "-"
                        required_str = "Yes" if param.required else "No"
                        lines.append(
                            f"<tr><td><code>{param.name}</code></td><td><code>{param.type_name}</code></td><td>{required_str}</td><td>{default_str}</td><td>{param.description}</td></tr>"
                        )

                    lines.append("</table>")

                    # Parameter options
                    for param in api.parameters:
                        if param.options:
                            lines.append(
                                f"<p><strong>{param.name} options</strong>: {', '.join(param.options)}</p>"
                            )

                # Return value
                lines.append("<h4>Returns</h4>")
                lines.append(f"<p><strong>Type:</strong> <code>{api.return_type}</code></p>")
                lines.append(f"<p><strong>Description:</strong> {api.return_description}</p>")

                # Tags
                if api.tags:
                    lines.append("<div class='tags'>")
                    for tag in api.tags:
                        lines.append(f"<span class='tag'>{tag}</span>")
                    lines.append("</div>")

                # Examples
                if api.examples:
                    lines.append("<h4>Examples</h4>")
                    for example in api.examples:
                        lines.append(f"<pre class='example'>{example}</pre>")

                lines.append("</div>")

        # Footer
        lines.append("<hr>")
        lines.append("<h2>API Usage Tips</h2>")
        lines.append("<ul>")
        lines.append("<li>Always handle exceptions: Memory operations can fail due to database issues</li>")
        lines.append("<li>Use appropriate memory types: Choose the right layer for your data</li>")
        lines.append("<li>Consolidate periodically: Run consolidation to extract patterns</li>")
        lines.append("<li>Check health regularly: Use health_check() to monitor system status</li>")
        lines.append("</ul>")

        lines.append("<h2>Best Practices</h2>")
        lines.append("<ul>")
        lines.append("<li>Use tags to organize memories for easier recall</li>")
        lines.append("<li>Store context information with events for better temporal reasoning</li>")
        lines.append("<li>Consolidate after significant work sessions</li>")
        lines.append("<li>Use prospective memory for planning and scheduling</li>")
        lines.append("<li>Build knowledge graphs for complex relationships</li>")
        lines.append("</ul>")

        lines.append("</body>")
        lines.append("</html>")

        return "\n".join(lines)

    def generate_json(self) -> str:
        """Generate JSON documentation.

        Returns:
            JSON-formatted API documentation
        """
        docs = {
            "name": "MemoryAPI",
            "version": "1.0",
            "generated": datetime.now().isoformat(),
            "description": "Direct Python API for memory operations",
            "categories": {},
        }

        # Group APIs by category
        for category in self.registry.get_categories():
            apis = self.registry.discover_apis(category=category)
            docs["categories"][category.value] = [api.to_dict() for api in apis]

        return json.dumps(docs, indent=2)

    def save_markdown(self, filepath: str) -> None:
        """Save Markdown documentation to file.

        Args:
            filepath: Path to save file
        """
        content = self.generate_markdown()
        with open(filepath, "w") as f:
            f.write(content)
        logger.info(f"Saved Markdown docs to {filepath}")

    def save_html(self, filepath: str) -> None:
        """Save HTML documentation to file.

        Args:
            filepath: Path to save file
        """
        content = self.generate_html()
        with open(filepath, "w") as f:
            f.write(content)
        logger.info(f"Saved HTML docs to {filepath}")

    def save_json(self, filepath: str) -> None:
        """Save JSON documentation to file.

        Args:
            filepath: Path to save file
        """
        content = self.generate_json()
        with open(filepath, "w") as f:
            f.write(content)
        logger.info(f"Saved JSON docs to {filepath}")
