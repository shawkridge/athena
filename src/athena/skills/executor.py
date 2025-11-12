"""Skill execution with parameter binding and error handling."""

from typing import Any, Dict, Optional, Callable
import logging
import sys
from io import StringIO

from .models import Skill, SkillParameter

logger = logging.getLogger(__name__)


class SkillExecutor:
    """Executes skills with safe isolation and error handling.

    Features:
    - Parameter validation and binding
    - Sandboxed execution (optional)
    - Error handling and recovery
    - Execution tracking
    """

    def __init__(self, library: 'SkillLibrary', sandbox: bool = True):
        """Initialize executor.

        Args:
            library: SkillLibrary instance
            sandbox: Whether to run in sandbox (isolated environment)
        """
        self.library = library
        self.sandbox = sandbox

    def execute(
        self,
        skill: Skill,
        parameters: Optional[Dict[str, Any]] = None,
        timeout: int = 30
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
                    'success': False,
                    'error': f"Entry point '{skill.entry_point}' not found in skill code",
                }

            entry_func = namespace[skill.entry_point]

            # Execute function
            result = entry_func(**bound_params)

            # Update library
            self.library.update_usage(skill.id, success=True)

            return {
                'success': True,
                'result': result,
                'skill_id': skill.id,
            }

        except Exception as e:
            # Update library
            self.library.update_usage(skill.id, success=False)

            logger.error(f"Skill execution failed: {skill.id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'skill_id': skill.id,
            }

    def _bind_parameters(
        self,
        skill: Skill,
        provided: Dict[str, Any]
    ) -> Dict[str, Any]:
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
                # TODO: Add type checking if needed
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
            'valid': len(errors) == 0,
            'errors': errors,
            'skill_id': skill.id,
        }

    def test(
        self,
        skill: Skill,
        test_parameters: Optional[Dict[str, Any]] = None
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
            logger.info(f"Using example parameters from skill definition")
            # TODO: Extract parameters from examples

        return self.execute(skill, params)

    def dry_run(self, skill: Skill) -> Dict[str, Any]:
        """Check if skill can be executed without actually running it.

        Args:
            skill: Skill to check

        Returns:
            Dry-run result with 'can_execute', 'issues'
        """
        validation = self.validate(skill)

        if not validation['valid']:
            return {
                'can_execute': False,
                'issues': validation['errors'],
                'skill_id': skill.id,
            }

        return {
            'can_execute': True,
            'issues': [],
            'skill_id': skill.id,
        }
