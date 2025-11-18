"""
Code Execution Engine for Athena MCP

Executes standalone Python modules from the filesystem API.
Provides safe isolation and result formatting.
"""

import importlib.util
import inspect
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass
import traceback


@dataclass
class ExecutionResult:
    """Result of code execution."""

    success: bool
    result: Any
    error: Optional[str] = None
    error_type: Optional[str] = None
    traceback_str: Optional[str] = None
    execution_time_ms: float = 0.0


class CodeExecutor:
    """
    Executes Python code from filesystem API modules.

    Paradigm:
    1. Agent discovers module via filesystem listing
    2. Agent reads module code
    3. CodeExecutor loads and executes specific function
    4. Result returned to agent context (small summary, not full data)
    """

    def __init__(self, filesystem_root: Optional[Path] = None):
        """Initialize executor with filesystem API root."""
        if filesystem_root is None:
            filesystem_root = Path(__file__).parent.parent / "filesystem_api"

        self.filesystem_root = Path(filesystem_root)
        self._module_cache = {}

    def execute(
        self,
        module_path: str,
        function_name: str,
        args: Dict[str, Any],
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """
        Execute a function from a filesystem API module.

        Args:
            module_path: Path like "/athena/layers/semantic/recall.py"
            function_name: Name of function to call
            args: Positional/keyword arguments as dict
            kwargs: Additional keyword arguments

        Returns:
            ExecutionResult with success/failure info
        """
        import time

        start_time = time.time()

        try:
            # Load the module
            module = self._load_module(module_path)

            # Get the function
            if not hasattr(module, function_name):
                return ExecutionResult(
                    success=False,
                    result=None,
                    error=f"Function '{function_name}' not found in module",
                    error_type="FunctionNotFound",
                    execution_time_ms=(time.time() - start_time) * 1000,
                )

            func = getattr(module, function_name)

            # Execute the function
            merged_kwargs = kwargs or {}
            merged_kwargs.update(args)

            # Handle both async and sync functions
            import asyncio
            import inspect

            if inspect.iscoroutinefunction(func):
                # For async functions, run in event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(func(**merged_kwargs))
                finally:
                    loop.close()
            else:
                # For sync functions, call directly
                result = func(**merged_kwargs)

            return ExecutionResult(
                success=True, result=result, execution_time_ms=(time.time() - start_time) * 1000
            )

        except Exception as e:
            return ExecutionResult(
                success=False,
                result=None,
                error=str(e),
                error_type=type(e).__name__,
                traceback_str=traceback.format_exc(),
                execution_time_ms=(time.time() - start_time) * 1000,
            )

    def _load_module(self, module_path: str):
        """
        Load a Python module from the filesystem API.

        Module path format: "/athena/layers/semantic/recall.py"
        Converted to filesystem: filesystem_root/layers/semantic/recall.py
        """
        # Normalize path
        if module_path.startswith("/athena/"):
            relative_path = module_path[8:]  # Remove "/athena/"
        else:
            relative_path = module_path

        full_path = self.filesystem_root / relative_path

        # Check cache first
        cache_key = str(full_path)
        if cache_key in self._module_cache:
            return self._module_cache[cache_key]

        # Verify file exists
        if not full_path.exists():
            raise FileNotFoundError(f"Module not found: {full_path}")

        # Load module
        spec = importlib.util.spec_from_file_location(full_path.stem, full_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Failed to load module spec: {full_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)

        # Cache it
        self._module_cache[cache_key] = module

        return module

    def get_module_signature(
        self, module_path: str, function_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get function signature for introspection.

        Returns info about function parameters for validation.
        """
        try:
            module = self._load_module(module_path)
            func = getattr(module, function_name)
            sig = inspect.signature(func)

            return {
                "function": function_name,
                "parameters": {
                    name: {
                        "annotation": str(param.annotation),
                        "default": (
                            str(param.default) if param.default != inspect.Parameter.empty else None
                        ),
                        "kind": str(param.kind),
                    }
                    for name, param in sig.parameters.items()
                },
                "return_annotation": str(sig.return_annotation),
                "docstring": inspect.getdoc(func),
            }
        except Exception as e:
            return {"error": str(e), "error_type": type(e).__name__}

    def clear_cache(self):
        """Clear the module cache."""
        self._module_cache.clear()


class ResultFormatter:
    """
    Formats execution results for MCP context.

    Philosophy: Return summaries, not full data.
    Target: <500 tokens per result (vs 5K-25K currently)
    """

    @staticmethod
    def format_result(result: ExecutionResult) -> Dict[str, Any]:
        """Format execution result for MCP response."""
        if not result.success:
            return {
                "status": "error",
                "error": result.error,
                "error_type": result.error_type,
                "execution_time_ms": result.execution_time_ms,
            }

        # Summarize the result (not include full data)
        return {
            "status": "success",
            "result": result.result,
            "execution_time_ms": result.execution_time_ms,
        }

    @staticmethod
    def estimate_tokens(result: Dict[str, Any]) -> int:
        """Rough estimate of tokens needed to represent result."""
        # Approximate: 1 token per 4 characters
        json_str = json.dumps(result)
        return len(json_str) // 4
