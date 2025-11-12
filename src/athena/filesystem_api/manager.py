"""
Filesystem API Manager

Manages the filesystem-based API structure that enables code execution paradigm.
Handles directory listings, file reading, and progressive disclosure.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import asdict


class FilesystemAPIManager:
    """
    Provides filesystem API operations for progressive tool discovery.

    Architecture:
    - Directory tree: /athena/layers/{layer}/{operation}.py
    - Each .py file is standalone executable with docstring
    - Agents discover tools by:
      1. list_directory("/athena/layers") → discovers layers
      2. list_directory("/athena/layers/semantic") → discovers operations
      3. read_file("/athena/layers/semantic/recall.py") → gets code
      4. execute code locally with parameters
    """

    def __init__(self, root_path: Optional[Path] = None):
        """Initialize with filesystem root."""
        if root_path is None:
            root_path = Path(__file__).parent
        self.root_path = Path(root_path)

    def list_directory(self, path: str) -> Dict[str, Any]:
        """
        List contents of a directory in the filesystem API.

        Returns:
            {
                "path": "/athena/layers",
                "type": "directory",
                "contents": [
                    {"name": "episodic", "type": "directory"},
                    {"name": "semantic", "type": "directory"},
                    ...
                ]
            }
        """
        # Normalize path
        if path.startswith("/athena/"):
            rel_path = path[8:]
        elif path.startswith("/"):
            rel_path = path[1:]
        else:
            rel_path = path

        full_path = self.root_path / rel_path

        if not full_path.exists():
            return {
                "error": f"Directory not found: {path}",
                "path": path
            }

        if not full_path.is_dir():
            return {
                "error": f"Not a directory: {path}",
                "path": path
            }

        contents = []
        for item in sorted(full_path.iterdir()):
            if item.name.startswith("__pycache__") or item.name == "__init__.py":
                continue

            if item.is_dir():
                contents.append({
                    "name": item.name,
                    "type": "directory",
                    "path": f"/athena/{rel_path}/{item.name}".lstrip("/").replace("//", "/")
                })
            elif item.is_file() and item.suffix == ".py":
                contents.append({
                    "name": item.name,
                    "type": "file",
                    "path": f"/athena/{rel_path}/{item.name}".lstrip("/").replace("//", "/"),
                    "size_bytes": item.stat().st_size
                })

        return {
            "path": path,
            "type": "directory",
            "contents": contents
        }

    def read_file(self, path: str) -> Dict[str, Any]:
        """
        Read a Python module file from the filesystem API.

        Returns:
            {
                "path": "/athena/layers/semantic/recall.py",
                "type": "file",
                "content": "def search_memories(query: str) -> Dict[str, Any]: ...",
                "size_bytes": 1234
            }
        """
        # Normalize path
        if path.startswith("/athena/"):
            rel_path = path[8:]
        elif path.startswith("/"):
            rel_path = path[1:]
        else:
            rel_path = path

        full_path = self.root_path / rel_path

        if not full_path.exists():
            return {
                "error": f"File not found: {path}",
                "path": path
            }

        if not full_path.is_file():
            return {
                "error": f"Not a file: {path}",
                "path": path
            }

        try:
            with open(full_path, "r") as f:
                content = f.read()

            return {
                "path": path,
                "type": "file",
                "content": content,
                "size_bytes": full_path.stat().st_size,
                "language": "python"
            }
        except Exception as e:
            return {
                "error": f"Failed to read file: {str(e)}",
                "path": path
            }

    def get_api_schema(self) -> Dict[str, Any]:
        """
        Get schema of all available operations.

        Returns:
            {
                "layers": {
                    "episodic": {
                        "operations": [
                            {
                                "name": "search",
                                "path": "/athena/layers/episodic/search.py",
                                "docstring": "...",
                                "parameters": {...}
                            }
                        ]
                    }
                }
            }
        """
        from ..execution.code_executor import CodeExecutor

        executor = CodeExecutor(self.root_path)
        schema = {
            "version": "1.0",
            "paradigm": "code_execution",
            "root": "/athena",
            "layers": {}
        }

        layers_path = self.root_path / "layers"
        if not layers_path.exists():
            return schema

        for layer_dir in sorted(layers_path.iterdir()):
            if not layer_dir.is_dir():
                continue

            layer_name = layer_dir.name
            operations = []

            for op_file in sorted(layer_dir.iterdir()):
                if not op_file.is_file() or op_file.suffix != ".py":
                    continue
                if op_file.name.startswith("_"):
                    continue

                try:
                    # Try to extract function info
                    with open(op_file, "r") as f:
                        content = f.read()

                    # Extract docstring if it starts with def
                    operation_name = op_file.stem
                    path = f"/athena/layers/{layer_name}/{op_file.name}"

                    # Try to extract main function name and docstring
                    import re
                    func_match = re.search(r'def (\w+)\([^)]*\):\s*"""([^"]*?)"""', content)

                    docstring = ""
                    function_name = operation_name
                    if func_match:
                        function_name = func_match.group(1)
                        docstring = func_match.group(2).strip()

                    operations.append({
                        "name": operation_name,
                        "function": function_name,
                        "path": path,
                        "docstring": docstring,
                        "size_bytes": op_file.stat().st_size
                    })
                except Exception:
                    pass

            if operations:
                schema["layers"][layer_name] = {
                    "operations": operations
                }

        return schema

    def get_operation_info(self, layer: str, operation: str) -> Dict[str, Any]:
        """
        Get detailed info about a specific operation.

        Args:
            layer: Layer name (episodic, semantic, etc)
            operation: Operation name (search, recall, etc)

        Returns:
            {
                "layer": "semantic",
                "operation": "recall",
                "path": "/athena/layers/semantic/recall.py",
                "docstring": "...",
                "function": "search_memories",
                "parameters": {...}
            }
        """
        from ..execution.code_executor import CodeExecutor

        path = f"/athena/layers/{layer}/{operation}.py"
        full_path = self.root_path / f"layers/{layer}/{operation}.py"

        if not full_path.exists():
            return {"error": f"Operation not found: {layer}/{operation}"}

        try:
            with open(full_path, "r") as f:
                content = f.read()

            # Extract main function name and docstring
            import re
            func_match = re.search(r'def (\w+)\([^)]*\):\s*"""([^"]*?)"""', content, re.DOTALL)

            if func_match:
                function_name = func_match.group(1)
                docstring = func_match.group(2).strip()
            else:
                # Try without docstring
                func_match = re.search(r'def (\w+)\(', content)
                function_name = func_match.group(1) if func_match else operation
                docstring = ""

            executor = CodeExecutor(self.root_path)
            sig = executor.get_module_signature(path, function_name)

            return {
                "layer": layer,
                "operation": operation,
                "path": path,
                "function": function_name,
                "docstring": docstring,
                "signature": sig,
                "size_bytes": full_path.stat().st_size
            }
        except Exception as e:
            return {
                "error": f"Failed to get operation info: {str(e)}",
                "layer": layer,
                "operation": operation
            }
