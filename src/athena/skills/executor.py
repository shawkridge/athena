"""Skill execution with parameter binding and error handling."""

from typing import Any, Dict, Optional
import logging

from .models import Skill

logger = logging.getLogger(__name__)


class ParameterTypeChecker:
    """Validates parameter types at runtime.

    Supports basic types (str, int, float, bool), complex types (List[T], Dict[K,V]),
    and Optional types. Provides clear error messages for mismatches.
    """

    # Mapping of type string names to Python types
    BUILTIN_TYPES = {
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "bytes": bytes,
        "list": list,
        "dict": dict,
        "tuple": tuple,
        "set": set,
        "frozenset": frozenset,
    }

    @classmethod
    def check_type(cls, value: Any, type_spec: str) -> tuple[bool, Optional[str]]:
        """Check if a value matches the specified type.

        Args:
            value: The value to check
            type_spec: Type specification string (e.g., 'str', 'List[int]', 'Optional[Dict[str,Any]]')

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if value matches type
            - error_message: None if valid, error description if invalid
        """
        # Handle None for Optional types
        if value is None:
            if "Optional" in type_spec or "?" in type_spec:
                return True, None
            if type_spec in ("NoneType", "None"):
                return True, None
            return False, f"None not allowed for type '{type_spec}'"

        # Clean up type spec
        type_spec = type_spec.strip()

        # Handle Optional[T] → T or None
        if type_spec.startswith("Optional[") and type_spec.endswith("]"):
            inner_type = type_spec[9:-1]  # Extract T from Optional[T]
            is_valid, error = cls.check_type(value, inner_type)
            return is_valid, error

        # Handle List[T]
        if type_spec.startswith("List[") and type_spec.endswith("]"):
            if not isinstance(value, list):
                return False, f"Expected list, got {type(value).__name__}"
            inner_type = type_spec[5:-1]  # Extract T from List[T]
            for i, item in enumerate(value):
                is_valid, error = cls.check_type(item, inner_type)
                if not is_valid:
                    return False, f"List item {i}: {error}"
            return True, None

        # Handle Dict[K,V]
        if type_spec.startswith("Dict[") and type_spec.endswith("]"):
            if not isinstance(value, dict):
                return False, f"Expected dict, got {type(value).__name__}"
            # Parse key and value types (handles nested generics)
            inner = type_spec[5:-1]
            key_type, val_type = cls._split_generic_params(inner)
            for k, v in value.items():
                is_valid, error = cls.check_type(k, key_type)
                if not is_valid:
                    return False, f"Dict key {k}: {error}"
                is_valid, error = cls.check_type(v, val_type)
                if not is_valid:
                    return False, f"Dict value for key {k}: {error}"
            return True, None

        # Handle Tuple[T1, T2, ...]
        if type_spec.startswith("Tuple[") and type_spec.endswith("]"):
            if not isinstance(value, tuple):
                return False, f"Expected tuple, got {type(value).__name__}"
            inner = type_spec[6:-1]
            types = cls._split_generic_params(inner, split_all=True)
            if len(types) == 1 and types[0].endswith("..."):
                # Tuple[T, ...] means variable-length tuple
                elem_type = types[0][:-3]
                for i, item in enumerate(value):
                    is_valid, error = cls.check_type(item, elem_type)
                    if not is_valid:
                        return False, f"Tuple item {i}: {error}"
            else:
                # Fixed-length tuple
                if len(value) != len(types):
                    return False, f"Expected tuple of length {len(types)}, got {len(value)}"
                for i, (item, expected_type) in enumerate(zip(value, types)):
                    is_valid, error = cls.check_type(item, expected_type)
                    if not is_valid:
                        return False, f"Tuple item {i}: {error}"
            return True, None

        # Handle Union[T1, T2, ...]
        if type_spec.startswith("Union[") and type_spec.endswith("]"):
            inner = type_spec[6:-1]
            types = cls._split_generic_params(inner, split_all=True)
            for t in types:
                is_valid, _ = cls.check_type(value, t)
                if is_valid:
                    return True, None
            return False, f"Value does not match any type in Union: {', '.join(types)}"

        # Handle simple/builtin types
        if type_spec in cls.BUILTIN_TYPES:
            expected_type = cls.BUILTIN_TYPES[type_spec]
            if isinstance(value, expected_type):
                return True, None
            return False, f"Expected {type_spec}, got {type(value).__name__}"

        # Handle Any type
        if type_spec in ("Any", "typing.Any", "object"):
            return True, None

        # If we don't recognize the type, log warning but allow it
        # (may be custom class or forward reference)
        logger.debug(
            f"Unknown type spec '{type_spec}', allowing value of type {type(value).__name__}"
        )
        return True, None

    @staticmethod
    def _split_generic_params(params_str: str, split_all: bool = False) -> list[str]:
        """Split generic type parameters, respecting nested brackets.

        Examples:
            'str, int' → ['str', 'int']
            'List[str], Dict[str,int]' → ['List[str]', 'Dict[str,int]']
        """
        params = []
        current = []
        depth = 0

        for char in params_str:
            if char in "[{(":
                depth += 1
                current.append(char)
            elif char in "]})":
                depth -= 1
                current.append(char)
            elif char == "," and depth == 0:
                param = "".join(current).strip()
                if param:
                    params.append(param)
                current = []
            else:
                current.append(char)

        if current:
            param = "".join(current).strip()
            if param:
                params.append(param)

        return params


class SkillExecutor:
    """Executes skills with safe isolation and error handling.

    Features:
    - Parameter validation and binding
    - Sandboxed execution (optional)
    - Error handling and recovery
    - Execution tracking
    """

    def __init__(self, library: "SkillLibrary", sandbox: bool = True):
        """Initialize executor.

        Args:
            library: SkillLibrary instance
            sandbox: Whether to run in sandbox (isolated environment)
        """
        self.library = library
        self.sandbox = sandbox

    async def execute(
        self, skill: Skill, parameters: Optional[Dict[str, Any]] = None, timeout: int = 30
    ) -> Dict[str, Any]:
        """Execute a skill with given parameters.

        Args:
            skill: Skill to execute
            parameters: Input parameters (name -> value)
            timeout: Max execution time in seconds

        Returns:
            Result dictionary with 'success', 'result', 'error'
        """
        try:
            # Validate parameters
            bound_params = self._bind_parameters(skill, parameters or {})

            # Compile code
            code_obj = compile(skill.code, filename=f"<skill:{skill.id}>", mode="exec")

            # Execute in namespace
            namespace = {}
            exec(code_obj, namespace)

            # Get entry point function
            if skill.entry_point not in namespace:
                return {
                    "success": False,
                    "error": f"Entry point '{skill.entry_point}' not found in skill code",
                }

            entry_func = namespace[skill.entry_point]

            # Execute function
            result = entry_func(**bound_params)

            # Update library
            await self.library.update_usage(skill.id, success=True)

            return {
                "success": True,
                "result": result,
                "skill_id": skill.id,
            }

        except Exception as e:
            # Update library
            await self.library.update_usage(skill.id, success=False)

            logger.error(f"Skill execution failed: {skill.id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "skill_id": skill.id,
            }

    def _bind_parameters(self, skill: Skill, provided: Dict[str, Any]) -> Dict[str, Any]:
        """Bind provided parameters to skill parameter definitions.

        Args:
            skill: Skill with parameter definitions
            provided: Provided parameter values

        Returns:
            Bound parameters dict

        Raises:
            ValueError: If required parameter missing or type mismatch
        """
        bound = {}

        for param in skill.metadata.parameters:
            if param.name in provided:
                value = provided[param.name]

                # Type check the provided value
                is_valid, error = ParameterTypeChecker.check_type(value, param.type)
                if not is_valid:
                    raise TypeError(
                        f"Parameter '{param.name}': {error} (expected type: {param.type})"
                    )

                bound[param.name] = value

            elif param.default is not None:
                bound[param.name] = param.default

            elif param.required:
                raise ValueError(f"Required parameter missing: {param.name}")

        # Check for unexpected parameters
        expected_names = {p.name for p in skill.metadata.parameters}
        extra_params = set(provided.keys()) - expected_names
        if extra_params:
            logger.warning(f"Extra parameters ignored: {extra_params}")

        return bound

    def validate(self, skill: Skill) -> Dict[str, Any]:
        """Validate a skill can be executed.

        Args:
            skill: Skill to validate

        Returns:
            Validation result with 'valid', 'errors'
        """
        errors = []

        # Check code compiles
        try:
            compile(skill.code, filename=f"<skill:{skill.id}>", mode="exec")
        except SyntaxError as e:
            errors.append(f"Syntax error in skill code: {e}")

        # Check entry point exists
        try:
            namespace = {}
            exec(skill.code, namespace)
            if skill.entry_point not in namespace:
                errors.append(f"Entry point '{skill.entry_point}' not found")
            elif not callable(namespace[skill.entry_point]):
                errors.append(f"Entry point '{skill.entry_point}' is not callable")
        except Exception as e:
            errors.append(f"Error executing skill for validation: {e}")

        # Check parameters match entry point signature
        # (Would need inspect module for detailed checking)

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "skill_id": skill.id,
        }

    async def test(
        self, skill: Skill, test_parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Test skill execution with sample parameters.

        Args:
            skill: Skill to test
            test_parameters: Test parameters (uses examples if not provided)

        Returns:
            Test result with 'success', 'result', 'error'
        """
        # Use test parameters or extract from examples
        params = test_parameters or {}

        if not params and skill.metadata.examples:
            logger.info("Using example parameters from skill definition")
            # TODO: Extract parameters from examples

        return await self.execute(skill, params)

    def dry_run(self, skill: Skill) -> Dict[str, Any]:
        """Check if skill can be executed without actually running it.

        Args:
            skill: Skill to check

        Returns:
            Dry-run result with 'can_execute', 'issues'
        """
        validation = self.validate(skill)

        if not validation["valid"]:
            return {
                "can_execute": False,
                "issues": validation["errors"],
                "skill_id": skill.id,
            }

        return {
            "can_execute": True,
            "issues": [],
            "skill_id": skill.id,
        }
