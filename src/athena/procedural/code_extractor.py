"""Extract executable code from procedure definitions.

This module provides ProcedureCodeExtractor, which converts procedure templates,
steps, and examples into executable Python code suitable for storing in git.
"""

import ast
import logging
import re
from typing import Optional, List, Dict, Tuple

from .models import Procedure, ExecutableProcedure

logger = logging.getLogger(__name__)


class ProcedureCodeExtractor:
    """Extracts and generates executable code from procedure definitions.

    Handles:
    - Converting procedure templates into executable functions
    - Extracting parameters and generating function signatures
    - Converting steps into executable code
    - Validating generated code syntax
    - Handling special cases (bash commands, file operations, etc.)
    """

    def __init__(self, procedure: Procedure):
        """Initialize code extractor.

        Args:
            procedure: Procedure to extract code from
        """
        self.procedure = procedure
        self.generated_code = ""
        self.extraction_confidence = 0.0

    def extract(self) -> Tuple[Optional[str], float]:
        """Extract executable code from procedure.

        Returns:
            Tuple of (code_string, confidence_score)
            - code_string: Executable Python code (None if extraction failed)
            - confidence_score: 0.0-1.0 confidence in generated code
        """
        try:
            # Build code from available sources in priority order
            code = self._build_function_signature()

            if self.procedure.code:
                # If procedure already has code, use it directly
                code += self.procedure.code
                self.extraction_confidence = 0.95
            elif self.procedure.steps:
                # Convert steps to executable code
                code += self._convert_steps_to_code()
                self.extraction_confidence = 0.7
            elif self.procedure.template:
                # Convert template to executable code
                code += self._convert_template_to_code()
                self.extraction_confidence = 0.6
            else:
                logger.warning(f"No extractable code found in procedure {self.procedure.name}")
                return None, 0.0

            # Validate generated code
            if not self._validate_code(code):
                logger.error(f"Generated code validation failed for {self.procedure.name}")
                return None, 0.0

            self.generated_code = code
            return code, self.extraction_confidence

        except Exception as e:
            logger.error(f"Code extraction failed for {self.procedure.name}: {e}")
            return None, 0.0

    def _build_function_signature(self) -> str:
        """Build Python function signature from procedure definition.

        Returns:
            Function signature with docstring and parameters
        """
        func_name = self._sanitize_function_name(self.procedure.name)

        # Extract parameters from steps or procedure fields
        params = self._extract_parameters()

        # Build parameter list
        param_str = ", ".join([f"{p['name']}: {p['type']}" for p in params])
        if param_str:
            param_str = f", {param_str}"

        # Build function header
        code = f"def {func_name}(context: dict{param_str}) -> dict:\n"
        code += f'    """{self.procedure.description or self.procedure.name}\n'
        code += self._build_docstring(params)
        code += '    """\n'

        return code

    def _build_docstring(self, params: List[Dict]) -> str:
        """Build docstring from procedure metadata.

        Args:
            params: List of parameter dicts

        Returns:
            Docstring body (excluding opening/closing quotes)
        """
        docstring = ""

        if params:
            docstring += "    Args:\n"
            docstring += "        context: Execution context with shared state\n"
            for param in params:
                param_name = param.get("name")
                param_desc = param.get("description", param.get("name"))
                docstring += f"        {param_name}: {param_desc}\n"

        if self.procedure.returns:
            docstring += f"    Returns:\n        {self.procedure.returns}\n"

        return docstring

    def _extract_parameters(self) -> List[Dict]:
        """Extract parameters from procedure definition.

        Returns:
            List of dicts with name, type, description
        """
        params = []

        # Look for {{variable}} patterns in template
        if self.procedure.template:
            var_pattern = r"\{\{(\w+)\}\}"
            for match in re.finditer(var_pattern, self.procedure.template):
                var_name = match.group(1)
                params.append(
                    {
                        "name": var_name,
                        "type": "str",
                        "description": f"Template variable: {var_name}",
                    }
                )

        # Extract from steps
        if self.procedure.steps:
            for step in self.procedure.steps:
                if isinstance(step, dict):
                    if "variables" in step:
                        for var_name in step["variables"]:
                            if not any(p["name"] == var_name for p in params):
                                params.append(
                                    {
                                        "name": var_name,
                                        "type": "str",
                                        "description": f"Step variable: {var_name}",
                                    }
                                )

        return params

    def _convert_steps_to_code(self) -> str:
        """Convert procedure steps into executable code.

        Returns:
            Executable code implementation
        """
        code = "    # Extracted from procedure steps\n"
        code += "    results = {}\n\n"

        if not self.procedure.steps:
            return code + "    return {'success': True, 'results': results}\n"

        for i, step in enumerate(self.procedure.steps, 1):
            if isinstance(step, dict):
                step_code = self._convert_single_step(step, i)
                code += step_code + "\n"
            elif isinstance(step, str):
                code += f"    # Step {i}: {step}\n"

        code += "    return {'success': True, 'results': results}\n"
        return code

    def _convert_single_step(self, step: Dict, step_num: int) -> str:
        """Convert a single step definition to code.

        Args:
            step: Step definition dict
            step_num: Step number

        Returns:
            Code for this step
        """
        code = f"    # Step {step_num}\n"

        if "name" in step:
            code += f"    # {step['name']}\n"

        if "action" in step:
            action = step["action"]
            if action.startswith("bash:") or action.startswith("command:"):
                # Extract command
                cmd = action.replace("bash:", "").replace("command:", "").strip()
                code += "    import subprocess\n"
                code += f"    result = subprocess.run('{cmd}', shell=True, capture_output=True, text=True)\n"
                code += f"    results['step_{step_num}_output'] = result.stdout\n"
            elif action.startswith("file:"):
                # File operation
                file_op = action.replace("file:", "").strip()
                code += f"    # File operation: {file_op}\n"
            else:
                # Generic code execution
                code += f"    {action}\n"

        if "validate" in step:
            code += f"    # Validation: {step['validate']}\n"

        return code.rstrip()

    def _convert_template_to_code(self) -> str:
        """Convert procedure template into executable code.

        Returns:
            Executable code implementation
        """
        code = "    # Converted from procedure template\n"
        code += "    template = r'''\n"

        # Indent template
        for line in self.procedure.template.split("\n"):
            code += f"    {line}\n"

        code += "    '''\n\n"

        # Add template rendering code
        code += "    # Render template with provided variables\n"
        code += "    try:\n"
        code += "        rendered = template\n"
        code += "        for key, value in context.items():\n"
        code += "            rendered = rendered.replace(f'{{{{{key}}}}}', str(value))\n"
        code += "        return {'success': True, 'rendered': rendered}\n"
        code += "    except Exception as e:\n"
        code += "        return {'success': False, 'error': str(e)}\n"

        return code

    def _sanitize_function_name(self, name: str) -> str:
        """Convert procedure name to valid Python function name.

        Args:
            name: Procedure name

        Returns:
            Valid Python function name
        """
        # Replace spaces and special characters with underscores
        name = re.sub(r"[^a-zA-Z0-9_]", "_", name.lower())
        # Remove leading digits
        name = re.sub(r"^[0-9]+", "", name)
        # Remove trailing underscores
        name = name.rstrip("_")
        # Ensure it's not empty
        return name if name else "procedure"

    def _validate_code(self, code: str) -> bool:
        """Validate that generated code is syntactically correct Python.

        Args:
            code: Python code to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            ast.parse(code)
            return True
        except SyntaxError as e:
            logger.error(f"Syntax error in generated code: {e}")
            return False

    def get_confidence_analysis(self) -> Dict:
        """Get detailed confidence analysis for generated code.

        Returns:
            Dict with confidence breakdown
        """
        analysis = {
            "overall_confidence": self.extraction_confidence,
            "code_source": "unknown",
            "factors": {},
        }

        if self.procedure.code:
            analysis["code_source"] = "direct_code"
            analysis["factors"]["has_direct_code"] = 1.0
            analysis["factors"]["steps_quality"] = 0.0
        elif self.procedure.steps:
            analysis["code_source"] = "converted_steps"
            analysis["factors"]["steps_count"] = min(1.0, len(self.procedure.steps) / 10)
            analysis["factors"]["steps_completeness"] = 0.7
        elif self.procedure.template:
            analysis["code_source"] = "converted_template"
            analysis["factors"]["template_length"] = min(1.0, len(self.procedure.template) / 1000)
            analysis["factors"]["template_complexity"] = 0.5

        analysis["factors"]["validation_passed"] = (
            1.0 if self._validate_code(self.generated_code) else 0.0
        )

        return analysis

    def to_executable_procedure(self) -> Optional[ExecutableProcedure]:
        """Convert extracted code to ExecutableProcedure model.

        Returns:
            ExecutableProcedure if extraction successful, None otherwise
        """
        code, confidence = self.extract()
        if not code:
            return None

        return ExecutableProcedure(
            procedure_id=self.procedure.id or 0,
            name=self.procedure.name,
            category=self.procedure.category,
            code=code,
            code_version="1.0.0",
            code_language="python",
            code_generated_at=self.procedure.created_at,
            code_generation_confidence=confidence,
            description=self.procedure.description,
            returns=None,
            examples=self.procedure.examples,
            preconditions=[],
            postconditions=[],
        )


def extract_code_from_procedure(procedure: Procedure) -> Tuple[Optional[str], float]:
    """Convenience function to extract code from a procedure.

    Args:
        procedure: Procedure to extract from

    Returns:
        Tuple of (code_string, confidence_score)
    """
    extractor = ProcedureCodeExtractor(procedure)
    return extractor.extract()
