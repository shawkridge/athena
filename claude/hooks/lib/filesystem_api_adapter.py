"""
Filesystem API Adapter for Claude Hooks

Bridges Claude hooks with Athena's filesystem API code execution paradigm.
Implements progressive disclosure, code reading, and local execution.

Philosophy: Models are great at navigating filesystems. Discover → Read → Execute → Summarize.
"""

import os
import json
from typing import Dict, Any, Optional, List
from pathlib import Path


class FilesystemAPIAdapter:
    """
    Adapter that provides hooks with filesystem API methods.

    Implements the code execution paradigm:
    1. Discover operations via filesystem
    2. Read operation code
    3. Execute locally
    4. Return summaries (never full data)
    """

    def __init__(self, athena_root: Optional[Path] = None):
        """Initialize adapter with Athena filesystem API root."""
        if athena_root is None:
            athena_root = Path(__file__).parent.parent.parent.parent / "src" / "athena" / "filesystem_api"

        self.athena_root = Path(athena_root)
        self._validate_root()

    def _validate_root(self):
        """Verify filesystem API root exists."""
        if not self.athena_root.exists():
            raise ValueError(f"Athena filesystem API root not found: {self.athena_root}")

    # ========================================================================
    # DISCOVERY METHODS (Progressive Disclosure)
    # ========================================================================

    def list_layers(self) -> Dict[str, Any]:
        """
        List available memory layers.

        Returns directory structure for agent to explore.
        Agent learns what layers exist without loading definitions.
        """
        layers_dir = self.athena_root / "layers"

        if not layers_dir.exists():
            return {"error": "Layers directory not found"}

        layers = []
        for layer_dir in sorted(layers_dir.iterdir()):
            if not layer_dir.is_dir() or layer_dir.name.startswith("_"):
                continue

            layers.append({
                "name": layer_dir.name,
                "path": f"/athena/layers/{layer_dir.name}",
                "operations": self._count_operations(layer_dir)
            })

        return {
            "total_layers": len(layers),
            "layers": layers,
            "message": "Use read_operation() to load specific operation code"
        }

    def list_operations_in_layer(self, layer: str) -> Dict[str, Any]:
        """
        List operations available in a specific layer.

        Agent can then choose which operation to execute.
        """
        layer_dir = self.athena_root / "layers" / layer

        if not layer_dir.exists():
            return {"error": f"Layer not found: {layer}"}

        if not layer_dir.is_dir():
            return {"error": f"Not a directory: {layer}"}

        operations = []
        for op_file in sorted(layer_dir.iterdir()):
            if not op_file.is_file() or op_file.suffix != ".py" or op_file.name.startswith("_"):
                continue

            operations.append({
                "name": op_file.stem,
                "path": f"/athena/layers/{layer}/{op_file.name}",
                "size_bytes": op_file.stat().st_size
            })

        return {
            "layer": layer,
            "operation_count": len(operations),
            "operations": operations,
            "message": f"Choose an operation and call read_operation() to see the code"
        }

    def list_cross_layer_operations(self) -> Dict[str, Any]:
        """List cross-layer operations (search_all, health_check, etc)."""
        ops_dir = self.athena_root / "operations"

        if not ops_dir.exists():
            return {"error": "Operations directory not found"}

        operations = []
        for op_file in sorted(ops_dir.iterdir()):
            if not op_file.is_file() or op_file.suffix != ".py" or op_file.name.startswith("_"):
                continue

            operations.append({
                "name": op_file.stem,
                "path": f"/athena/operations/{op_file.name}",
                "size_bytes": op_file.stat().st_size
            })

        return {
            "operation_count": len(operations),
            "operations": operations,
            "message": "Cross-layer operations for multi-layer queries"
        }

    # ========================================================================
    # CODE READING METHODS (Understanding Before Execution)
    # ========================================================================

    def read_operation(self, layer: str, operation: str) -> Dict[str, Any]:
        """
        Read operation code.

        Agent reads this to understand what the operation does and what parameters it takes.
        """
        op_file = self.athena_root / "layers" / layer / f"{operation}.py"

        if not op_file.exists():
            return {
                "error": f"Operation not found: {layer}/{operation}",
                "path": f"/athena/layers/{layer}/{operation}.py"
            }

        try:
            with open(op_file, "r") as f:
                code = f.read()

            # Extract docstring
            docstring = self._extract_docstring(code)

            return {
                "layer": layer,
                "operation": operation,
                "path": f"/athena/layers/{layer}/{operation}.py",
                "docstring": docstring,
                "code": code,
                "message": "Review the code. When ready, call execute_operation() with parameters"
            }

        except Exception as e:
            return {
                "error": f"Failed to read operation: {str(e)}",
                "layer": layer,
                "operation": operation
            }

    def read_cross_layer_operation(self, operation: str) -> Dict[str, Any]:
        """Read code for a cross-layer operation."""
        op_file = self.athena_root / "operations" / f"{operation}.py"

        if not op_file.exists():
            return {"error": f"Operation not found: {operation}"}

        try:
            with open(op_file, "r") as f:
                code = f.read()

            docstring = self._extract_docstring(code)

            return {
                "operation": operation,
                "path": f"/athena/operations/{operation}.py",
                "docstring": docstring,
                "code": code
            }

        except Exception as e:
            return {"error": f"Failed to read operation: {str(e)}"}

    # ========================================================================
    # EXECUTION METHODS (Local Processing, Summary Returns)
    # ========================================================================

    def execute_operation(
        self,
        layer: str,
        operation: str,
        args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute an operation and return summary.

        This is where the magic happens:
        - Operation code executes locally (in execution sandbox)
        - All filtering/processing happens locally
        - Only summaries return to model context
        - Result is <300 tokens, not 15K

        Args:
            layer: Memory layer name
            operation: Operation name
            args: Arguments to pass to operation

        Returns:
            Summary result (never full data objects)
        """
        try:
            from athena.execution.code_executor import CodeExecutor

            executor = CodeExecutor()
            module_path = f"/athena/layers/{layer}/{operation}.py"

            # Find main function name (usually matches operation name)
            function_name = self._get_function_name(layer, operation)

            # Add db_path if not provided
            if "db_path" not in args:
                args["db_path"] = os.path.expanduser("~/.athena/memory.db")

            # Execute locally - this is the key difference!
            # All data processing happens here, not in model context
            result = executor.execute(module_path, function_name, args)

            if result.success:
                return {
                    "status": "success",
                    "layer": layer,
                    "operation": operation,
                    "result": result.result,
                    "execution_time_ms": result.execution_time_ms,
                    "note": "Result is a summary (statistics, IDs, counts). For full details, call get_details() with an ID."
                }
            else:
                return {
                    "status": "error",
                    "layer": layer,
                    "operation": operation,
                    "error": result.error,
                    "error_type": result.error_type
                }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__
            }

    def execute_cross_layer_operation(
        self,
        operation: str,
        args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a cross-layer operation."""
        try:
            from athena.execution.code_executor import CodeExecutor

            executor = CodeExecutor()
            module_path = f"/athena/operations/{operation}.py"
            function_name = self._get_function_name("operations", operation)

            if "db_path" not in args:
                args["db_path"] = os.path.expanduser("~/.athena/memory.db")

            result = executor.execute(module_path, function_name, args)

            if result.success:
                return {
                    "status": "success",
                    "operation": operation,
                    "result": result.result,
                    "execution_time_ms": result.execution_time_ms
                }
            else:
                return {
                    "status": "error",
                    "operation": operation,
                    "error": result.error
                }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    # ========================================================================
    # DETAIL METHODS (Drill-Down When Necessary)
    # ========================================================================

    def get_detail(self, layer: str, detail_type: str, detail_id: str) -> Dict[str, Any]:
        """
        Get full details for a specific item (use sparingly!).

        When operation returns summary with IDs, call this to get full details
        for specific items you need more information about.

        Example: After semantic_search returns top_5_ids, call get_detail()
        to get full memory object for the most relevant one.
        """
        try:
            from athena.execution.code_executor import CodeExecutor

            executor = CodeExecutor()

            # Build function name (get_{detail_type}_details)
            function_name = f"get_{detail_type}_details"
            module_path = f"/athena/layers/{layer}/{detail_type}.py"

            result = executor.execute(module_path, function_name, {
                "db_path": os.path.expanduser("~/.athena/memory.db"),
                "id": detail_id
            })

            if result.success:
                return {
                    "status": "success",
                    "detail_id": detail_id,
                    "detail": result.result
                }
            else:
                return {
                    "status": "error",
                    "error": result.error
                }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _count_operations(self, layer_dir: Path) -> int:
        """Count operations in a layer directory."""
        count = 0
        for f in layer_dir.iterdir():
            if f.is_file() and f.suffix == ".py" and not f.name.startswith("_"):
                count += 1
        return count

    def _extract_docstring(self, code: str) -> str:
        """Extract docstring from Python code."""
        import re
        match = re.search(r'"""(.*?)"""', code, re.DOTALL)
        if match:
            return match.group(1).strip()
        return "No docstring found"

    def _get_function_name(self, layer: str, operation: str) -> str:
        """Determine main function name in operation file."""
        # By convention, function name matches operation name or is first function
        # Try common patterns: operation_name, search_*, get_*
        return operation.replace("-", "_")

    def get_api_schema(self) -> Dict[str, Any]:
        """
        Get full API schema.

        Useful for documentation and understanding available operations.
        """
        return {
            "paradigm": "code_execution_with_filesystem_api",
            "layers": self.list_layers(),
            "cross_layer": self.list_cross_layer_operations(),
            "message": "Use list_layers() and list_operations_in_layer() for progressive discovery"
        }


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_adapter(athena_root: Optional[Path] = None) -> FilesystemAPIAdapter:
    """Get a filesystem API adapter instance."""
    return FilesystemAPIAdapter(athena_root)


def discover_memory_operations(query: Optional[str] = None) -> Dict[str, Any]:
    """
    Discover memory-related operations.

    Convenient method for common discovery patterns.
    """
    adapter = get_adapter()

    # List semantic layer (most common for memory queries)
    semantic_ops = adapter.list_operations_in_layer("semantic")

    return {
        "message": "Memory operations available in semantic layer",
        "query": query,
        "operations": semantic_ops
    }


def quick_search(query: str, layer: str = "semantic") -> Dict[str, Any]:
    """
    Quick search helper.

    Demonstrates the full discover → read → execute → summarize flow.
    """
    adapter = get_adapter()

    # Step 1: Discover available operations
    ops = adapter.list_operations_in_layer(layer)

    # For semantic search, the operation is usually "recall"
    search_op = "recall" if layer == "semantic" else "search"

    # Step 2: Read operation code (agent understands what it does)
    code_info = adapter.read_operation(layer, search_op)

    # Step 3: Execute locally
    result = adapter.execute_operation(layer, search_op, {"query": query})

    return {
        "step_1_discover": ops,
        "step_2_code": code_info.get("docstring", ""),
        "step_3_execute": result,
        "message": f"Searched '{query}' in {layer} layer. Got summary with {result.get('result', {}).get('total_results', '?')} results."
    }
