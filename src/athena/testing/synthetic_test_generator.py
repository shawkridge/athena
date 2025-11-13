"""Generate synthetic test inputs for dream procedures."""

import ast
import inspect
import logging
from typing import Any, Dict, List, Tuple, Optional, Type
from dataclasses import dataclass
import random
import string

logger = logging.getLogger(__name__)


@dataclass
class ParameterInfo:
    """Information about a function parameter."""

    name: str
    annotation: Optional[Type] = None
    default: Any = None
    is_optional: bool = False


class SyntheticTestGenerator:
    """Generate synthetic test inputs based on procedure signatures."""

    # Type generation strategies
    SCALAR_SAMPLES = {
        "int": [0, 1, -1, 42, 1000, -1000],
        "float": [0.0, 1.0, -1.0, 3.14, 100.5, -50.25],
        "str": ["", "test", "hello world", "x" * 100],
        "bool": [True, False],
    }

    def __init__(self, seed: Optional[int] = None):
        """Initialize synthetic test generator.

        Args:
            seed: Random seed for reproducibility
        """
        if seed is not None:
            random.seed(seed)

    def generate_test_inputs(
        self,
        code: str,
        num_variants: int = 5,
    ) -> List[Dict[str, Any]]:
        """Generate synthetic test inputs from procedure code.

        Args:
            code: Python code containing procedure
            num_variants: Number of input variants to generate

        Returns:
            List of dictionaries with test inputs
        """
        # Extract function signature
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            logger.error(f"Could not parse code: {e}")
            return []

        # Find first function definition
        func_def = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_def = node
                break

        if not func_def:
            logger.warning("No function definition found in code")
            return []

        # Extract parameters
        params = self._extract_parameters(func_def)

        # Generate variants
        variants = []
        for i in range(num_variants):
            variant = self._generate_inputs_for_params(params, variant_index=i)
            if variant:
                variants.append(variant)

        return variants

    def _extract_parameters(self, func_def: ast.FunctionDef) -> List[ParameterInfo]:
        """Extract parameters from function definition.

        Args:
            func_def: AST FunctionDef node

        Returns:
            List of ParameterInfo objects
        """
        params = []

        # Process regular arguments
        args = func_def.args
        num_args = len(args.args)
        num_defaults = len(args.defaults)

        # Arguments with defaults
        defaults_start = num_args - num_defaults
        for i, arg in enumerate(args.args):
            is_optional = i >= defaults_start
            default = None
            if is_optional:
                default_idx = i - defaults_start
                default = args.defaults[default_idx]

            # Get type annotation
            annotation = None
            if arg.annotation:
                annotation = self._extract_annotation(arg.annotation)

            params.append(
                ParameterInfo(
                    name=arg.arg,
                    annotation=annotation,
                    default=default,
                    is_optional=is_optional,
                )
            )

        return params

    @staticmethod
    def _extract_annotation(annotation_node: ast.expr) -> Optional[str]:
        """Extract type annotation as string.

        Args:
            annotation_node: AST annotation node

        Returns:
            Type annotation string
        """
        if isinstance(annotation_node, ast.Name):
            return annotation_node.id
        elif isinstance(annotation_node, ast.Constant):
            return str(annotation_node.value)
        else:
            return None

    def _generate_inputs_for_params(
        self,
        params: List[ParameterInfo],
        variant_index: int = 0,
    ) -> Dict[str, Any]:
        """Generate input values for parameters.

        Args:
            params: List of parameters
            variant_index: Index for variant selection (for deterministic variation)

        Returns:
            Dictionary of parameter values
        """
        inputs = {}

        for param in params:
            value = self._generate_value(
                param.annotation,
                param.is_optional,
                param.default,
                variant_index,
            )
            if value is not None:
                inputs[param.name] = value

        return inputs

    def _generate_value(
        self,
        annotation: Optional[str],
        is_optional: bool,
        default: Any,
        variant_index: int,
    ) -> Any:
        """Generate a single test value.

        Args:
            annotation: Type annotation
            is_optional: Whether parameter is optional
            default: Default value
            variant_index: Index for variant selection

        Returns:
            Generated test value
        """
        # Handle optional parameters
        if is_optional:
            if variant_index % 2 == 0 and default is not None:
                return default

        # Generate based on type annotation
        if annotation:
            annotation_lower = annotation.lower()

            if "int" in annotation_lower:
                samples = self.SCALAR_SAMPLES.get("int", [42])
                return samples[variant_index % len(samples)]

            elif "float" in annotation_lower:
                samples = self.SCALAR_SAMPLES.get("float", [3.14])
                return samples[variant_index % len(samples)]

            elif "str" in annotation_lower:
                samples = self.SCALAR_SAMPLES.get("str", ["test"])
                return samples[variant_index % len(samples)]

            elif "bool" in annotation_lower:
                return variant_index % 2 == 0

            elif "list" in annotation_lower:
                return self._generate_list(annotation, variant_index)

            elif "dict" in annotation_lower:
                return self._generate_dict(variant_index)

            elif "tuple" in annotation_lower:
                return self._generate_tuple(annotation, variant_index)
        else:
            # If no annotation, try common type hints based on context
            # For parameters without annotations, generate a sensible default
            return 42

        # Default: return a sensible default
        return 42

    def _generate_list(
        self,
        annotation: str,
        variant_index: int,
    ) -> list:
        """Generate a list for testing.

        Args:
            annotation: Type annotation string
            variant_index: Variant index

        Returns:
            Generated list
        """
        # Extract element type if available (e.g., "List[int]")
        element_type = self._extract_generic_type(annotation)

        # Generate list size based on variant
        size = max(1, variant_index % 5)

        if element_type == "int":
            return list(range(size))
        elif element_type == "str":
            return [f"item_{i}" for i in range(size)]
        elif element_type == "float":
            return [float(i) * 1.5 for i in range(size)]
        else:
            return list(range(size))

    def _generate_dict(self, variant_index: int) -> dict:
        """Generate a dict for testing.

        Args:
            variant_index: Variant index

        Returns:
            Generated dictionary
        """
        size = max(1, variant_index % 3)
        return {f"key_{i}": f"value_{i}" for i in range(size)}

    def _generate_tuple(
        self,
        annotation: str,
        variant_index: int,
    ) -> tuple:
        """Generate a tuple for testing.

        Args:
            annotation: Type annotation string
            variant_index: Variant index

        Returns:
            Generated tuple
        """
        # Extract element types if available
        types = self._extract_tuple_types(annotation)

        if types:
            elements = []
            for t in types:
                elements.append(self._generate_value(t, False, None, variant_index))
            return tuple(elements)
        else:
            # Default: small tuple of integers
            size = max(2, variant_index % 4)
            return tuple(range(size))

    @staticmethod
    def _extract_generic_type(annotation: str) -> Optional[str]:
        """Extract generic type from annotation (e.g., "List[int]" -> "int").

        Args:
            annotation: Type annotation string

        Returns:
            Generic type if found
        """
        if "[" in annotation and "]" in annotation:
            start = annotation.index("[") + 1
            end = annotation.index("]")
            return annotation[start:end].strip()
        return None

    @staticmethod
    def _extract_tuple_types(annotation: str) -> List[str]:
        """Extract tuple element types from annotation.

        Args:
            annotation: Type annotation string (e.g., "Tuple[int, str, float]")

        Returns:
            List of element types
        """
        if "[" in annotation and "]" in annotation:
            start = annotation.index("[") + 1
            end = annotation.index("]")
            types_str = annotation[start:end]
            return [t.strip() for t in types_str.split(",")]
        return []

    def generate_edge_case_inputs(
        self,
        code: str,
    ) -> List[Dict[str, Any]]:
        """Generate edge case test inputs.

        Args:
            code: Python code containing procedure

        Returns:
            List of edge case input dictionaries
        """
        # Extract parameters
        try:
            tree = ast.parse(code)
            func_def = None
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_def = node
                    break

            if not func_def:
                return []

            params = self._extract_parameters(func_def)
        except Exception as e:
            logger.error(f"Could not extract parameters: {e}")
            return []

        edge_cases = []

        # Empty/zero cases
        empty_case = {}
        for param in params:
            if param.annotation and "list" in param.annotation.lower():
                empty_case[param.name] = []
            elif param.annotation and "dict" in param.annotation.lower():
                empty_case[param.name] = {}
            elif param.annotation and "str" in param.annotation.lower():
                empty_case[param.name] = ""
            else:
                empty_case[param.name] = 0

        if empty_case:
            edge_cases.append(empty_case)

        # Large inputs
        large_case = {}
        for param in params:
            if param.annotation and "list" in param.annotation.lower():
                large_case[param.name] = list(range(10000))
            elif param.annotation and "str" in param.annotation.lower():
                large_case[param.name] = "x" * 100000
            elif param.annotation and "int" in param.annotation.lower():
                large_case[param.name] = 2**31 - 1
            else:
                large_case[param.name] = None

        if large_case:
            edge_cases.append(large_case)

        # Negative/null cases
        null_case = {}
        for param in params:
            if not param.is_optional:
                null_case[param.name] = None

        if null_case:
            edge_cases.append(null_case)

        return edge_cases

    def get_expected_output_type(
        self,
        code: str,
    ) -> Optional[str]:
        """Infer expected output type from function return annotation.

        Args:
            code: Python code containing procedure

        Returns:
            Expected output type string if found
        """
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if node.returns:
                        return self._extract_annotation(node.returns)
        except Exception as e:
            logger.error(f"Could not extract return type: {e}")

        return None
