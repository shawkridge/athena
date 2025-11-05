"""
Visuospatial Sketchpad: Spatial and visual information storage.

Purpose:
- Track current workspace (open files, directories)
- Maintain spatial relationships (file hierarchy)
- Store visual/spatial context

Key Features:
- Capacity: 7±2 items (same as phonological loop)
- Content: File paths, locations, spatial arrangements
- Integration: Works with editor/IDE state
"""

from typing import List, Optional, Dict
from datetime import datetime
import json
import os

from ..core.database import Database
from .models import WorkingMemoryItem, Component, ContentType


class VisuospatialSketchpad:
    """
    Visuospatial Sketchpad component of Baddeley's Working Memory model.

    Tracks current workspace awareness and spatial context.
    """

    def __init__(self, db: Database | str):
        # Accept either Database instance or path string
        if isinstance(db, Database):
            self.db = db
        else:
            self.db = Database(db)
        self.max_capacity = 7  # 7±2 capacity
        self.component = Component.VISUOSPATIAL

    # ========================================================================
    # File Tracking
    # ========================================================================

    def add_file(
        self,
        project_id: int,
        file_path: str,
        context: Optional[str] = None,
        importance: float = 0.7
    ) -> int:
        """
        Add file to visuospatial sketchpad.

        Args:
            project_id: Project identifier
            file_path: Path to file (absolute or relative)
            context: Optional context (e.g., "currently editing", "just viewed")
            importance: Importance score (default 0.7 - files are usually important)

        Returns:
            ID of created item
        """
        # Check capacity
        current_count = self._get_item_count(project_id)
        if current_count >= self.max_capacity:
            self._remove_oldest(project_id)

        # Normalize path
        file_path = os.path.normpath(file_path)

        # Create content
        content = f"File: {file_path}"
        if context:
            content += f"\nContext: {context}"

        # Store metadata about file
        metadata = {
            'file_path': file_path,
            'context': context,
            'file_type': self._infer_file_type(file_path),
            'directory': os.path.dirname(file_path),
            'filename': os.path.basename(file_path)
        }

        # Insert
        with self.db.conn:
            cursor = self.db.conn.execute("""
                INSERT INTO working_memory
                (project_id, content, content_type, component,
                 importance_score, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                project_id,
                content,
                ContentType.SPATIAL.value,
                self.component.value,
                importance,
                json.dumps(metadata)
            ))

            return cursor.lastrowid

    def add_directory(
        self,
        project_id: int,
        directory_path: str,
        context: Optional[str] = None
    ) -> int:
        """Add directory to workspace awareness."""
        directory_path = os.path.normpath(directory_path)

        content = f"Directory: {directory_path}"
        if context:
            content += f"\nContext: {context}"

        metadata = {
            'directory_path': directory_path,
            'context': context,
            'type': 'directory'
        }

        with self.db.conn:
            cursor = self.db.conn.execute("""
                INSERT INTO working_memory
                (project_id, content, content_type, component,
                 importance_score, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                project_id,
                content,
                ContentType.SPATIAL.value,
                self.component.value,
                0.6,  # Directories slightly less important than files
                json.dumps(metadata)
            ))

            return cursor.lastrowid

    def remove_file(self, project_id: int, file_path: str):
        """Remove file from sketchpad."""
        file_path = os.path.normpath(file_path)

        with self.db.conn:
            self.db.conn.execute("""
                DELETE FROM working_memory
                WHERE project_id = ?
                AND component = ?
                AND json_extract(metadata, '$.file_path') = ?
            """, (project_id, self.component.value, file_path))

    def update_file_context(
        self,
        project_id: int,
        file_path: str,
        context: str
    ):
        """Update context for tracked file."""
        file_path = os.path.normpath(file_path)

        with self.db.conn:
            # Get current item
            row = self.db.conn.execute("""
                SELECT id, metadata FROM working_memory
                WHERE project_id = ?
                AND component = ?
                AND json_extract(metadata, '$.file_path') = ?
            """, (project_id, self.component.value, file_path)).fetchone()

            if row:
                metadata = json.loads(row['metadata'])
                metadata['context'] = context

                # Update
                self.db.conn.execute("""
                    UPDATE working_memory
                    SET metadata = ?,
                        last_accessed = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (json.dumps(metadata), row['id']))

    # ========================================================================
    # Workspace Queries
    # ========================================================================

    def get_current_workspace(self, project_id: int) -> Dict:
        """
        Get current workspace context.

        Returns:
            Dict with files, directories, and workspace metadata
        """
        with self.db.conn:
            rows = self.db.conn.execute("""
                SELECT * FROM working_memory
                WHERE project_id = ? AND component = ?
                ORDER BY last_accessed DESC
            """, (project_id, self.component.value)).fetchall()

            files = []
            directories = []

            for row in rows:
                metadata = json.loads(row['metadata']) if row['metadata'] else {}

                if 'file_path' in metadata:
                    files.append({
                        'path': metadata['file_path'],
                        'context': metadata.get('context'),
                        'type': metadata.get('file_type'),
                        'last_accessed': row['last_accessed']
                    })
                elif 'directory_path' in metadata:
                    directories.append({
                        'path': metadata['directory_path'],
                        'context': metadata.get('context'),
                        'last_accessed': row['last_accessed']
                    })

            return {
                'files': files,
                'directories': directories,
                'file_count': len(files),
                'directory_count': len(directories),
                'total_items': len(rows),
                'capacity': self.max_capacity,
                'capacity_status': self._get_capacity_status(len(rows))
            }

    def get_files_in_directory(
        self,
        project_id: int,
        directory_path: str
    ) -> List[Dict]:
        """Get all tracked files within a directory."""
        directory_path = os.path.normpath(directory_path)

        with self.db.conn:
            rows = self.db.conn.execute("""
                SELECT * FROM working_memory
                WHERE project_id = ?
                AND component = ?
                AND json_extract(metadata, '$.directory') = ?
            """, (project_id, self.component.value, directory_path)).fetchall()

            files = []
            for row in rows:
                metadata = json.loads(row['metadata']) if row['metadata'] else {}
                if 'file_path' in metadata:
                    files.append({
                        'path': metadata['file_path'],
                        'filename': metadata.get('filename'),
                        'context': metadata.get('context'),
                        'last_accessed': row['last_accessed']
                    })

            return files

    def is_file_tracked(self, project_id: int, file_path: str) -> bool:
        """Check if file is currently tracked."""
        file_path = os.path.normpath(file_path)

        with self.db.conn:
            result = self.db.conn.execute("""
                SELECT COUNT(*) as count FROM working_memory
                WHERE project_id = ?
                AND component = ?
                AND json_extract(metadata, '$.file_path') = ?
            """, (project_id, self.component.value, file_path)).fetchone()

            return result['count'] > 0

    def get_recently_accessed_files(
        self,
        project_id: int,
        limit: int = 5
    ) -> List[str]:
        """
        Get most recently accessed files.

        Args:
            project_id: Project identifier
            limit: Number of files to return

        Returns:
            List of file paths sorted by recency
        """
        with self.db.conn:
            rows = self.db.conn.execute("""
                SELECT metadata FROM working_memory
                WHERE project_id = ?
                AND component = ?
                AND json_extract(metadata, '$.file_path') IS NOT NULL
                ORDER BY last_accessed DESC
                LIMIT ?
            """, (project_id, self.component.value, limit)).fetchall()

            files = []
            for row in rows:
                metadata = json.loads(row['metadata'])
                files.append(metadata['file_path'])

            return files

    def add_item(
        self,
        project_id: int,
        content: str,
        file_path: Optional[str] = None,
        importance: float = 0.7
    ) -> int:
        """
        Add item to visuospatial sketchpad.

        Args:
            project_id: Project identifier
            content: Content text
            file_path: Optional file path
            importance: Importance score

        Returns:
            ID of created item
        """
        # Check capacity
        current_count = self._get_item_count(project_id)
        if current_count >= self.max_capacity:
            self._remove_oldest(project_id)

        # Build metadata
        metadata = {}
        if file_path:
            file_path = os.path.normpath(file_path)
            metadata = {
                'file_path': file_path,
                'file_type': self._infer_file_type(file_path),
                'directory': os.path.dirname(file_path),
                'filename': os.path.basename(file_path)
            }

        # Insert with content as-is
        with self.db.conn:
            cursor = self.db.conn.execute("""
                INSERT INTO working_memory
                (project_id, content, content_type, component, importance_score, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                project_id,
                content,
                ContentType.SPATIAL.value,
                self.component.value,
                importance,
                json.dumps(metadata) if metadata else None
            ))
            return cursor.lastrowid

    def get_items(self, project_id: int) -> List:
        """Get all items in visuospatial sketchpad."""
        with self.db.conn:
            rows = self.db.conn.execute("""
                SELECT * FROM working_memory
                WHERE project_id = ? AND component = ?
                ORDER BY last_accessed DESC
            """, (project_id, self.component.value)).fetchall()
            return [self._row_to_item(row) for row in rows]

    def get_item(self, item_id: int):
        """Get single item by ID."""
        with self.db.conn:
            row = self.db.conn.execute("""
                SELECT * FROM working_memory WHERE id = ?
            """, (item_id,)).fetchone()
            if not row:
                return None
            return self._row_to_item(row)

    def update_file_path(self, item_id: int, new_path: str):
        """Update file path for an item."""
        new_path = os.path.normpath(new_path)
        with self.db.conn:
            # Get current metadata
            row = self.db.conn.execute("""
                SELECT metadata FROM working_memory WHERE id = ?
            """, (item_id,)).fetchone()

            if row:
                metadata = json.loads(row['metadata']) if row['metadata'] else {}
                metadata['file_path'] = new_path
                metadata['directory'] = os.path.dirname(new_path)
                metadata['filename'] = os.path.basename(new_path)

                # Update content as well
                content = f"File: {new_path}"
                if metadata.get('context'):
                    content += f"\nContext: {metadata['context']}"

                self.db.conn.execute("""
                    UPDATE working_memory
                    SET metadata = ?, content = ?, last_accessed = datetime('now')
                    WHERE id = ?
                """, (json.dumps(metadata), content, item_id))

    def find_by_directory(self, project_id: int, directory: str) -> List:
        """Find all items in specific directory."""
        directory = os.path.normpath(directory)
        with self.db.conn:
            rows = self.db.conn.execute("""
                SELECT * FROM working_memory
                WHERE project_id = ? AND component = ?
                AND (json_extract(metadata, '$.directory') = ?
                     OR json_extract(metadata, '$.file_path') LIKE ?)
            """, (project_id, self.component.value, directory, f"{directory}%")).fetchall()
            return [self._row_to_item(row) for row in rows]

    # ========================================================================
    # Spatial Relationships
    # ========================================================================

    def get_file_hierarchy(self, project_id: int) -> Dict:
        """
        Get hierarchical view of tracked files.

        Returns:
            Tree structure of directories and files
        """
        workspace = self.get_current_workspace(project_id)

        # Build hierarchy
        hierarchy = {}

        for file_info in workspace['files']:
            path = file_info['path']
            parts = path.split(os.sep)

            current = hierarchy
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            # Add file
            filename = parts[-1]
            current[filename] = {
                'type': 'file',
                'context': file_info['context'],
                'last_accessed': file_info['last_accessed']
            }

        return hierarchy

    def get_spatial_neighbors(self, project_id: int, file_path: str) -> List:
        """Get spatially neighboring items in same directory."""
        from pathlib import Path
        parent_dir = str(Path(file_path).parent)

        with self.db.conn:
            rows = self.db.conn.execute("""
                SELECT * FROM working_memory
                WHERE project_id = ? AND component = ?
                AND json_extract(metadata, '$.file_path') LIKE ?
                AND json_extract(metadata, '$.file_path') != ?
            """, (project_id, self.component.value, f"{parent_dir}%", file_path)).fetchall()
            return [self._row_to_item(row) for row in rows]

    # ========================================================================
    # Capacity Management
    # ========================================================================

    def clear(self, project_id: int):
        """Clear all items from visuospatial sketchpad."""
        with self.db.conn:
            self.db.conn.execute("""
                DELETE FROM working_memory
                WHERE project_id = ? AND component = ?
            """, (project_id, self.component.value))

    def _get_item_count(self, project_id: int) -> int:
        """Get current item count."""
        with self.db.conn:
            result = self.db.conn.execute("""
                SELECT COUNT(*) as count FROM working_memory
                WHERE project_id = ? AND component = ?
            """, (project_id, self.component.value)).fetchone()

            return result['count']

    def _remove_oldest(self, project_id: int, count: int = 1):
        """Remove oldest items to make space."""
        with self.db.conn:
            rows = self.db.conn.execute("""
                SELECT id FROM working_memory
                WHERE project_id = ? AND component = ?
                ORDER BY last_accessed ASC
                LIMIT ?
            """, (project_id, self.component.value, count)).fetchall()

            for row in rows:
                self.db.conn.execute("""
                    DELETE FROM working_memory WHERE id = ?
                """, (row['id'],))

    def _get_capacity_status(self, count: int) -> str:
        """Get capacity status string."""
        if count >= self.max_capacity:
            return 'full'
        elif count >= self.max_capacity - 2:
            return 'near_full'
        else:
            return 'available'

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _infer_file_type(self, file_path: str) -> str:
        """Infer file type from extension."""
        extension = os.path.splitext(file_path)[1].lower()

        type_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'header',
            '.hpp': 'header',
            '.md': 'markdown',
            '.txt': 'text',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.xml': 'xml',
            '.html': 'html',
            '.css': 'css',
            '.sql': 'sql',
            '.sh': 'shell',
            '.rs': 'rust',
            '.go': 'go'
        }

        return type_map.get(extension, 'unknown')

    def get_statistics(self, project_id: int) -> Dict:
        """Get visuospatial sketchpad statistics."""
        workspace = self.get_current_workspace(project_id)

        # Count file types
        file_types = {}
        for file in workspace['files']:
            file_type = file.get('type', 'unknown')
            file_types[file_type] = file_types.get(file_type, 0) + 1

        return {
            'total_items': workspace['total_items'],
            'file_count': workspace['file_count'],
            'directory_count': workspace['directory_count'],
            'capacity_used': workspace['total_items'] / self.max_capacity,
            'file_types': file_types,
            'capacity_status': workspace['capacity_status']
        }

    def _row_to_item(self, row):
        """Convert database row to item object with attributes."""
        from types import SimpleNamespace
        from datetime import datetime

        metadata = json.loads(row['metadata']) if row['metadata'] else {}

        # Calculate current activation with decay
        created = datetime.fromisoformat(row['created_at'])
        last_accessed = datetime.fromisoformat(row['last_accessed'])
        time_since_access = (datetime.now() - last_accessed).total_seconds()
        decay_rate = row['decay_rate']
        importance = row['importance_score']

        import math
        adaptive_rate = decay_rate * (1 - importance * 0.5)
        current_activation = row['activation_level'] * math.exp(-adaptive_rate * time_since_access)

        # Extract file path info
        file_path = metadata.get('file_path', None)
        depth = 0
        parent_path = None

        if file_path:
            parts = file_path.split(os.sep)
            depth = len(parts) - 1
            parent_path = os.path.dirname(file_path) if depth > 0 else None

        # Check if chunk_size and source_items columns exist
        chunk_size = row['chunk_size'] if 'chunk_size' in row.keys() else None
        source_items = row['source_items'] if 'source_items' in row.keys() else None

        return SimpleNamespace(
            id=row['id'],
            project_id=row['project_id'],
            content=row['content'],
            file_path=file_path,
            depth=depth,
            parent_path=parent_path,
            activation_level=row['activation_level'],
            current_activation=current_activation,
            importance_score=importance,
            created_at=created,
            last_accessed=last_accessed,
            metadata=metadata,
            chunk_size=chunk_size,
            source_items=source_items
        )
