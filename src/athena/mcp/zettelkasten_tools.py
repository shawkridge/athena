"""MCP tools for A-MEM Zettelkasten memory evolution."""

from mcp.types import Tool, TextContent
from typing import Any

from ..associations.zettelkasten import ZettelkastenEvolution
from ..core.database import Database


def get_zettelkasten_tools() -> list[Tool]:
    """Get Zettelkasten MCP tool definitions."""
    return [
        Tool(
            name="create_memory_version",
            description="Create a new version of a memory with SHA256 hashing for change detection. Auto-triggers attribute updates.",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "integer",
                        "description": "ID of memory to version"
                    },
                    "content": {
                        "type": "string",
                        "description": "New content for this version"
                    },
                },
                "required": ["memory_id", "content"],
            }
        ),
        Tool(
            name="get_memory_evolution_history",
            description="Get complete evolution history of a memory (all versions with timestamps).",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "integer",
                        "description": "ID of memory to get history for"
                    },
                },
                "required": ["memory_id"],
            }
        ),
        Tool(
            name="compute_memory_attributes",
            description="Compute auto-generated attributes: importance_score (0-1 based on access frequency + recency), context_tags (auto-extracted topics), evolution_stage (nascent/developing/mature/stable), related_count (bidirectional links).",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "integer",
                        "description": "ID of memory to compute attributes for"
                    },
                },
                "required": ["memory_id"],
            }
        ),
        Tool(
            name="get_memory_attributes",
            description="Retrieve cached auto-computed attributes for a memory.",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "integer",
                        "description": "ID of memory"
                    },
                },
                "required": ["memory_id"],
            }
        ),
        Tool(
            name="create_hierarchical_index",
            description="Create a new hierarchical index node using Luhmann numbering system (1, 1.1, 1.1.1, etc.). Auto-generates index IDs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "Project ID"
                    },
                    "parent_id": {
                        "type": ["string", "null"],
                        "description": "Parent index ID (null for root)"
                    },
                    "label": {
                        "type": "string",
                        "description": "Human-readable label for this index",
                        "default": "Untitled"
                    },
                },
                "required": ["project_id"],
            }
        ),
        Tool(
            name="assign_memory_to_index",
            description="Assign a memory to a hierarchical index position.",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "integer",
                        "description": "Memory ID to assign"
                    },
                    "index_id": {
                        "type": "string",
                        "description": "Index ID (e.g., '1.2.3')"
                    },
                },
                "required": ["memory_id", "index_id"],
            }
        ),
    ]


class ZettelkastenMCPHandlers:
    """MCP handlers for Zettelkasten operations."""

    def __init__(self, db: Database):
        """Initialize handlers.

        Args:
            db: Database connection
        """
        self.db = db
        self.zettel = ZettelkastenEvolution(db)

    async def create_memory_version(self, memory_id: int, content: str) -> TextContent:
        """Create memory version."""
        try:
            version = self.zettel.create_memory_version(memory_id, content)
            return TextContent(
                type="text",
                text=f"""✓ Created version {version.version} for memory {memory_id}
Hash: {version.hash[:16]}...
Created: {version.created_at.isoformat()}"""
            )
        except Exception as e:
            return TextContent(type="text", text=f"❌ Error: {str(e)}")

    async def get_memory_evolution_history(self, memory_id: int) -> TextContent:
        """Get memory evolution history."""
        try:
            history = self.zettel.get_memory_evolution_history(memory_id)
            if not history:
                return TextContent(type="text", text=f"No versions found for memory {memory_id}")

            lines = [f"Evolution History for Memory {memory_id}:\n"]
            for v in history:
                lines.append(f"  v{v.version}: {v.created_at.isoformat()}")
                lines.append(f"    Hash: {v.hash[:16]}...")
                lines.append(f"    Content: {v.content[:80]}...")

            return TextContent(type="text", text="\n".join(lines))
        except Exception as e:
            return TextContent(type="text", text=f"❌ Error: {str(e)}")

    async def compute_memory_attributes(self, memory_id: int) -> TextContent:
        """Compute memory attributes."""
        try:
            attr = self.zettel.compute_memory_attributes(memory_id)
            return TextContent(
                type="text",
                text=f"""✓ Computed attributes for memory {memory_id}:

Importance Score: {attr.importance_score:.2f} (0-1 scale)
  - Based on access frequency (60%) + recency (40%)

Evolution Stage: {attr.evolution_stage}
  - nascent (0 versions) → developing → mature → stable (10+)

Context Tags: {', '.join(attr.context_tags) if attr.context_tags else 'None'}
  - Auto-extracted from content

Related Memories: {attr.related_count}
  - Bidirectional links to other memories

Last Evolved: {attr.last_evolved_at.isoformat()}"""
            )
        except Exception as e:
            return TextContent(type="text", text=f"❌ Error: {str(e)}")

    async def get_memory_attributes(self, memory_id: int) -> TextContent:
        """Get cached memory attributes."""
        try:
            attr = self.zettel.get_memory_attributes(memory_id)
            if not attr:
                return TextContent(type="text", text=f"No attributes found for memory {memory_id}. Try compute_memory_attributes() first.")

            return TextContent(
                type="text",
                text=f"""Memory {memory_id} Attributes:

Importance: {attr.importance_score:.2f}
Stage: {attr.evolution_stage}
Tags: {', '.join(attr.context_tags)}
Related: {attr.related_count}"""
            )
        except Exception as e:
            return TextContent(type="text", text=f"❌ Error: {str(e)}")

    async def create_hierarchical_index(self, project_id: int, parent_id: str = None, label: str = "Untitled") -> TextContent:
        """Create hierarchical index."""
        try:
            index = self.zettel.create_hierarchical_index(project_id, parent_id, label)
            return TextContent(
                type="text",
                text=f"""✓ Created index: {index.index_id}
Label: {index.label}
Parent: {index.parent_id or 'None (root)'}
Depth: {index.depth}

Luhmann numbering examples:
  1.1.1 → Child of 1.1 → Child of 1"""
            )
        except Exception as e:
            return TextContent(type="text", text=f"❌ Error: {str(e)}")

    async def assign_memory_to_index(self, memory_id: int, index_id: str) -> TextContent:
        """Assign memory to index."""
        try:
            self.zettel.assign_memory_to_index(memory_id, index_id)
            return TextContent(
                type="text",
                text=f"✓ Assigned memory {memory_id} to index {index_id}"
            )
        except Exception as e:
            return TextContent(type="text", text=f"❌ Error: {str(e)}")
