"""
Spatial Context Integration for Memory Retrieval.

Integrates spatial (file path) context into memory ranking to prioritize
memories from the same or related code locations.
"""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from pathlib import Path

from athena.core.database import Database

logger = logging.getLogger(__name__)


@dataclass
class SpatialContext:
    """Spatial (file path) context."""

    file_path: str
    directory: str
    depth: int  # Path depth (e.g., /src/auth/jwt.py = 3)
    component: str  # Component name (e.g., "auth")


class SpatialContextIntegration:
    """Integrates file path context into memory retrieval."""

    def __init__(self, db: Database, cwd: Optional[str] = None):
        """Initialize spatial context integration.

        Args:
            db: Database connection
            cwd: Current working directory for relative path resolution
        """
        self.db = db
        self.cwd = Path(cwd) if cwd else Path.cwd()

    def analyze_spatial_context(self, file_path: Optional[str]) -> SpatialContext:
        """Analyze spatial context of a file.

        Args:
            file_path: File path to analyze

        Returns:
            SpatialContext with hierarchical information
        """
        if not file_path:
            return SpatialContext(
                file_path="",
                directory="",
                depth=0,
                component="",
            )

        try:
            path = Path(file_path)

            # Get directory components
            parts = path.parts
            depth = len(parts)

            # Extract component name (usually first or second level)
            component = ""
            if depth >= 2:
                # Skip common prefixes like "src", "lib", "app"
                if parts[0] in ("src", "lib", "app", "code"):
                    component = parts[1] if len(parts) > 1 else parts[0]
                else:
                    component = parts[0]

            return SpatialContext(
                file_path=str(path),
                directory=str(path.parent),
                depth=depth,
                component=component,
            )

        except Exception as e:
            logger.debug(f"Spatial context analysis failed: {e}")
            return SpatialContext(
                file_path=str(file_path),
                directory="",
                depth=0,
                component="",
            )

    def calculate_spatial_proximity(
        self,
        context_a: SpatialContext,
        context_b: SpatialContext,
    ) -> float:
        """Calculate proximity score between two spatial contexts.

        Same component = 1.0, same directory = 0.8, same root = 0.5, different = 0.2

        Args:
            context_a: First spatial context
            context_b: Second spatial context

        Returns:
            Proximity score (0.0-1.0)
        """
        if not context_a.component or not context_b.component:
            return 0.0

        # Exact match = same component
        if context_a.component == context_b.component:
            return 1.0

        # Same directory
        if context_a.directory == context_b.directory:
            return 0.8

        # Same root directory
        if context_a.file_path.split("/")[0] == context_b.file_path.split("/")[0]:
            return 0.5

        # Different components
        return 0.2

    def find_memories_in_spatial_context(
        self,
        spatial_context: SpatialContext,
        radius: float = 0.5,  # Proximity threshold
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Find memories associated with similar spatial contexts.

        Uses spatial hierarchy to find related code in same/nearby areas.

        Args:
            spatial_context: Target spatial context
            radius: Proximity threshold (0.0-1.0)
            limit: Maximum results

        Returns:
            List of memories with spatial context
        """
        memories = []

        try:
            cursor = self.db.get_cursor()

            # Find episodic events with file context
            cursor.execute(
                """
                SELECT id, content, timestamp, layer, usefulness
                FROM episodic_events
                WHERE layer LIKE '%file%' OR content LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (f"%{spatial_context.component}%", limit * 2),
            )

            for row in cursor.fetchall():
                event_id, content, timestamp, layer, usefulness = row

                # Extract file path from content (simple heuristic)
                file_path = self._extract_file_path(content)
                if not file_path:
                    continue

                # Calculate proximity
                other_context = self.analyze_spatial_context(file_path)
                proximity = self.calculate_spatial_proximity(
                    spatial_context,
                    other_context,
                )

                # Only include if meets proximity threshold
                if proximity >= radius:
                    memories.append(
                        {
                            "id": event_id,
                            "content": content,
                            "timestamp": timestamp,
                            "layer": layer,
                            "usefulness": float(usefulness or 0.5),
                            "proximity": proximity,
                            "file_path": file_path,
                        }
                    )

            # Sort by proximity
            memories.sort(key=lambda m: m["proximity"], reverse=True)

            return memories[:limit]

        except Exception as e:
            logger.error(f"Spatial context search failed: {e}")
            return []

    def weight_memory_by_proximity(
        self,
        memories: List[Dict[str, Any]],
        current_context: SpatialContext,
    ) -> List[Dict[str, Any]]:
        """Boost memory scores based on spatial proximity.

        Memories from same component get +20% usefulness boost.

        Args:
            memories: List of memories with optional file paths
            current_context: Current spatial context

        Returns:
            Memories with adjusted usefulness scores
        """
        weighted = []

        for memory in memories:
            file_path = memory.get("file_path")
            if file_path:
                memory_context = self.analyze_spatial_context(file_path)
                proximity = self.calculate_spatial_proximity(
                    current_context,
                    memory_context,
                )

                # Boost usefulness by proximity
                original_usefulness = memory.get("usefulness", 0.5)
                boosted_usefulness = min(
                    1.0,
                    original_usefulness + (0.2 * proximity),
                )

                memory["usefulness_original"] = original_usefulness
                memory["usefulness"] = boosted_usefulness
                memory["spatial_boost"] = boosted_usefulness - original_usefulness

            weighted.append(memory)

        return weighted

    def build_spatial_context_hierarchy(
        self,
        root_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build hierarchical view of code organization.

        Useful for understanding project structure and file relationships.

        Args:
            root_path: Root path for hierarchy

        Returns:
            Dict with hierarchical structure
        """
        hierarchy = {
            "root": root_path or str(self.cwd),
            "components": {},
            "total_files": 0,
        }

        try:
            cursor = self.db.get_cursor()

            # Query all episodic events with file context
            cursor.execute(
                """
                SELECT DISTINCT content, layer
                FROM episodic_events
                WHERE layer LIKE '%file%'
                ORDER BY timestamp DESC
                """
            )

            components = {}

            for content, layer in cursor.fetchall():
                # Extract file path
                file_path = self._extract_file_path(content)
                if not file_path:
                    continue

                # Analyze context
                context = self.analyze_spatial_context(file_path)
                component = context.component or "root"

                if component not in components:
                    components[component] = {
                        "files": [],
                        "depth_avg": 0,
                    }

                components[component]["files"].append(file_path)
                hierarchy["total_files"] += 1

            # Calculate stats
            for component, info in components.items():
                depths = [len(Path(f).parts) for f in info["files"]]
                if depths:
                    info["depth_avg"] = sum(depths) / len(depths)
                    info["depth_max"] = max(depths)
                    info["file_count"] = len(info["files"])

            hierarchy["components"] = components

            return hierarchy

        except Exception as e:
            logger.error(f"Hierarchy building failed: {e}")
            return hierarchy

    def _extract_file_path(self, content: str) -> Optional[str]:
        """Extract file path from event content.

        Uses simple heuristics to find file paths in text.

        Args:
            content: Event content text

        Returns:
            File path if found
        """
        # Look for common path patterns
        patterns = [
            r"src/\S+\.py",
            r"lib/\S+\.js",
            r"app/\S+\.\w+",
            r"/\S+/\S+\.\w+",
        ]

        import re

        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(0)

        return None

    async def spatial_file_search(
        self,
        query: str,
        component_filter: Optional[str] = None,
    ) -> List[str]:
        """Search for files matching query in spatial context.

        Args:
            query: Search query (file name or component)
            component_filter: Filter by component

        Returns:
            List of matching file paths
        """
        try:
            cursor = self.db.get_cursor()

            sql = """
                SELECT DISTINCT content FROM episodic_events
                WHERE (content LIKE ? OR layer LIKE ?)
            """
            params = [f"%{query}%", f"%{query}%"]

            if component_filter:
                sql += " AND content LIKE ?"
                params.append(f"%{component_filter}%")

            sql += " ORDER BY timestamp DESC LIMIT 20"

            cursor.execute(sql, params)

            files = []
            for (content,) in cursor.fetchall():
                file_path = self._extract_file_path(content)
                if file_path:
                    files.append(file_path)

            return list(set(files))  # Remove duplicates

        except Exception as e:
            logger.error(f"Spatial file search failed: {e}")
            return []
