"""Spatial grounding for AI Coordination to Memory-MCP integration.

Links CodeContext files and execution locations to Memory-MCP's spatial
hierarchy layer, enabling spatial-aware memory retrieval and context binding.

This is the foundation of Phase 7.2 - enables Memory-MCP to understand
the code architecture and spatial scope of AI Coordination events.
"""

import json
from datetime import datetime
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from athena.core.database import Database
    from athena.ai_coordination.code_context import CodeContext


class SpatialGrounder:
    """Links AI Coordination code context to Memory-MCP spatial hierarchy.

    Purpose:
    - Map CodeContext file paths to spatial_hierarchy nodes
    - Track which files are relevant to which tasks
    - Link execution locations to code structure
    - Enable spatial-aware memory queries

    This enables queries like:
    - "What happened in src/auth/ recently?"
    - "Which files does this task modify?"
    - "What's the code scope of this goal?"
    """

    def __init__(self, db: "Database"):
        """Initialize SpatialGrounder.

        Args:
            db: Database connection
        """
        self.db = db
    def _ensure_schema(self):
        """Create spatial_grounding tables if they don't exist."""
        cursor = self.db.get_cursor()

        # Table: Integration links between coordination and memory layers
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS integration_links (
                id INTEGER PRIMARY KEY,
                source_type TEXT NOT NULL,  -- ExecutionTrace, CodeContext, etc
                source_id TEXT NOT NULL,    -- ID in coordination system
                target_type TEXT NOT NULL,  -- spatial_node, episodic_event, etc
                target_id INTEGER NOT NULL, -- ID in memory-mcp system
                link_type TEXT NOT NULL,    -- 'file_modified', 'file_read', 'scope', etc
                metadata TEXT,              -- JSON with link details
                created_at INTEGER NOT NULL,
                last_accessed INTEGER
            )
        """)

        # Table: Graph entity references (cross-layer)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS graph_entity_refs (
                id INTEGER PRIMARY KEY,
                entity_name TEXT NOT NULL,  -- function, class, file, etc
                entity_type TEXT NOT NULL,  -- 'file', 'function', 'class', 'module'
                source_layer TEXT NOT NULL, -- 'coordination', 'episodic', 'semantic'
                source_id INTEGER NOT NULL,
                target_layer TEXT,          -- layer it's referenced in
                target_id INTEGER,
                reference_type TEXT,        -- 'definition', 'usage', 'modification'
                metadata TEXT,              -- JSON with additional context
                created_at INTEGER NOT NULL
            )
        """)

        # Indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_integration_links_source
            ON integration_links(source_type, source_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_integration_links_target
            ON integration_links(target_type, target_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_graph_entity_name
            ON graph_entity_refs(entity_name, entity_type)
        """)

        # commit handled by cursor context

    def link_code_context_to_spatial(
        self,
        code_context: "CodeContext",
        episodic_event_id: int,
        task_id: Optional[str] = None
    ) -> int:
        """Link CodeContext files to spatial hierarchy.

        Args:
            code_context: CodeContext from AI Coordination
            episodic_event_id: ID of corresponding episodic event
            task_id: Optional task this code context applies to

        Returns:
            Number of spatial links created
        """
        cursor = self.db.get_cursor()
        link_count = 0
        now = int(datetime.now().timestamp() * 1000)

        # Link each file in code_context to spatial hierarchy
        if code_context.relevant_files:
            for file_path in code_context.relevant_files:
                metadata = {
                    "file_path": file_path,
                    "task_id": task_id,
                    "context_id": code_context.context_id,
                    "file_count": code_context.file_count,
                    "dependency_types": [str(d) for d in code_context.dependency_types] if code_context.dependency_types else [],
                }

                cursor.execute("""
                    INSERT INTO integration_links
                    (source_type, source_id, target_type, target_id, link_type, metadata, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    "CodeContext",
                    str(code_context.context_id),
                    "spatial_node",
                    episodic_event_id,
                    "file_scope",
                    json.dumps(metadata),
                    now
                ))

                link_count += 1

        # commit handled by cursor context
        return link_count

    def link_execution_location(
        self,
        execution_id: str,
        file_path: str,
        function_name: Optional[str],
        line_number: Optional[int],
        episodic_event_id: int
    ) -> int:
        """Link execution to specific code location.

        Args:
            execution_id: ID of execution in coordination system
            file_path: Path to file being executed
            function_name: Optional function name
            line_number: Optional line number
            episodic_event_id: Corresponding episodic event

        Returns:
            Link ID
        """
        cursor = self.db.get_cursor()
        now = int(datetime.now().timestamp() * 1000)

        metadata = {
            "file_path": file_path,
            "function_name": function_name,
            "line_number": line_number,
        }

        cursor.execute("""
            INSERT INTO integration_links
            (source_type, source_id, target_type, target_id, link_type, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            "ExecutionTrace",
            execution_id,
            "code_location",
            episodic_event_id,
            "execution_location",
            json.dumps(metadata),
            now
        ))

        link_id = cursor.lastrowid
        # commit handled by cursor context
        return link_id

    def get_files_for_task(self, task_id: str) -> list[str]:
        """Get files involved in a task.

        Args:
            task_id: Task identifier

        Returns:
            List of file paths
        """
        cursor = self.db.get_cursor()

        cursor.execute("""
            SELECT DISTINCT metadata
            FROM integration_links
            WHERE link_type = 'file_scope'
            AND metadata LIKE ?
        """, (f'%"task_id": "{task_id}"%',))

        files = []
        for row in cursor.fetchall():
            try:
                metadata = json.loads(row[0])
                if "file_path" in metadata:
                    files.append(metadata["file_path"])
            except (json.JSONDecodeError, KeyError):
                pass

        return files

    def get_task_scope(self, task_id: str) -> dict:
        """Get the code scope of a task.

        Args:
            task_id: Task identifier

        Returns:
            Dict with scope information
        """
        cursor = self.db.get_cursor()

        cursor.execute("""
            SELECT COUNT(DISTINCT metadata), metadata
            FROM integration_links
            WHERE link_type = 'file_scope'
            AND metadata LIKE ?
            LIMIT 1
        """, (f'%"task_id": "{task_id}"%',))

        row = cursor.fetchone()
        if not row:
            return {"task_id": task_id, "file_count": 0, "files": []}

        try:
            metadata = json.loads(row[1])
            return {
                "task_id": task_id,
                "file_count": metadata.get("file_count", 0),
                "files": [metadata.get("file_path", "")],
                "dependency_types": metadata.get("dependency_types", []),
            }
        except (json.JSONDecodeError, KeyError):
            return {"task_id": task_id, "file_count": 0, "files": []}

    def record_file_access(
        self,
        file_path: str,
        access_type: str,  # read, write, modify, create, delete
        execution_id: str,
        episodic_event_id: int
    ) -> int:
        """Record file access during execution.

        Args:
            file_path: Path to file accessed
            access_type: Type of access
            execution_id: Execution that caused access
            episodic_event_id: Corresponding episodic event

        Returns:
            Link ID
        """
        cursor = self.db.get_cursor()
        now = int(datetime.now().timestamp() * 1000)

        metadata = {
            "file_path": file_path,
            "access_type": access_type,
        }

        cursor.execute("""
            INSERT INTO integration_links
            (source_type, source_id, target_type, target_id, link_type, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            "ExecutionTrace",
            execution_id,
            "spatial_node",
            episodic_event_id,
            f"file_{access_type}",
            json.dumps(metadata),
            now
        ))

        link_id = cursor.lastrowid
        # commit handled by cursor context
        return link_id

    def get_execution_locations(self, execution_id: str) -> list[dict]:
        """Get all code locations accessed during execution.

        Args:
            execution_id: Execution identifier

        Returns:
            List of location dicts
        """
        cursor = self.db.get_cursor()

        cursor.execute("""
            SELECT metadata
            FROM integration_links
            WHERE source_type = 'ExecutionTrace'
            AND source_id = ?
            AND link_type IN ('execution_location', 'file_read', 'file_write', 'file_modify')
        """, (execution_id,))

        locations = []
        for row in cursor.fetchall():
            try:
                metadata = json.loads(row[0])
                locations.append(metadata)
            except json.JSONDecodeError:
                pass

        return locations

    def get_spatial_context(self, episodic_event_id: int) -> dict:
        """Get spatial context for an episodic event.

        Args:
            episodic_event_id: ID of episodic event

        Returns:
            Dict with spatial context
        """
        cursor = self.db.get_cursor()

        cursor.execute("""
            SELECT link_type, metadata
            FROM integration_links
            WHERE target_type IN ('spatial_node', 'code_location')
            AND target_id = ?
        """, (episodic_event_id,))

        spatial_context = {
            "files": set(),
            "locations": [],
            "accesses": {},
        }

        for link_type, metadata_json in cursor.fetchall():
            try:
                metadata = json.loads(metadata_json)
                if "file_path" in metadata:
                    spatial_context["files"].add(metadata["file_path"])
                if link_type.startswith("file_"):
                    access_type = link_type.replace("file_", "")
                    if access_type not in spatial_context["accesses"]:
                        spatial_context["accesses"][access_type] = []
                    spatial_context["accesses"][access_type].append(metadata.get("file_path"))
                if "function_name" in metadata:
                    spatial_context["locations"].append(metadata)
            except json.JSONDecodeError:
                pass

        spatial_context["files"] = list(spatial_context["files"])
        return spatial_context
