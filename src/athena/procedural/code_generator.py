"""Generate executable code for procedures using LLM reasoning.

This module provides ProcedureCodeGenerator, which uses Claude or local LLMs
to generate executable Python code from procedure definitions, with confidence
scoring and validation.
"""

import json
import logging
import re
from typing import Optional, Dict, Tuple, Any

from .models import Procedure

logger = logging.getLogger(__name__)


class CodeGenerationPrompt:
    """Generates optimized prompts for code generation from procedure definitions."""

    @staticmethod
    def build_procedure_context(procedure: Procedure) -> str:
        """Build rich context about the procedure."""
        parts = [
            f"Name: {procedure.name}",
            f"Category: {procedure.category}",
        ]

        if procedure.description:
            parts.append(f"Description: {procedure.description}")

        if procedure.applicable_contexts:
            parts.append(f"Applicable contexts: {', '.join(procedure.applicable_contexts)}")

        if procedure.template:
            parts.append(f"Template: {procedure.template}")

        if procedure.steps:
            parts.append("\nSteps:")
            for i, step in enumerate(procedure.steps, 1):
                if isinstance(step, dict):
                    step_text = step.get("description", str(step))
                else:
                    step_text = str(step)
                parts.append(f"  {i}. {step_text}")

        if procedure.examples:
            parts.append("\nExamples:")
            for i, example in enumerate(procedure.examples, 1):
                if isinstance(example, dict):
                    example_text = json.dumps(example, indent=2)
                else:
                    example_text = str(example)
                parts.append(f"  {i}. {example_text}")

        return "\n".join(parts)

    @staticmethod
    def build_code_generation_prompt(procedure: Procedure) -> str:
        """Build the main code generation prompt."""
        context = CodeGenerationPrompt.build_procedure_context(procedure)

        prompt = f"""You are a Python code generation expert. Your task is to convert the following procedure into clean, executable Python code.

PROCEDURE DEFINITION:
{context}

REQUIREMENTS:
1. Generate a complete, self-contained Python function
2. Function name should be: {CodeGenerationPrompt._sanitize_name(procedure.name)}
3. Include comprehensive docstring with description, args, returns
4. Handle all parameters from the procedure template/steps
5. Include error handling with try/except blocks
6. Add logging for debugging
7. Return results in a structured format (dict or object)
8. Code must be syntactically valid Python 3.9+
9. Include type hints for all parameters and return values
10. Make the code production-ready with proper error messages

PROCEDURE PARAMETERS:
Extract any parameters from the template ({{variable}}) or steps and include them as function arguments.

CODE STYLE:
- Use meaningful variable names
- Add comments for complex logic
- Keep functions under 50 lines if possible
- Use standard library only (no external dependencies unless necessary)

Generate ONLY the Python code, starting with the function definition. Do not include markdown code blocks or explanations."""

        return prompt

    @staticmethod
    def build_refinement_prompt(code: str, feedback: str) -> str:
        """Build a prompt to refine generated code based on feedback."""
        prompt = f"""Review and improve the following Python code based on this feedback:

ORIGINAL CODE:
```python
{code}
```

FEEDBACK:
{feedback}

Provide the improved code that addresses the feedback. Generate ONLY the refined Python code without explanations or markdown blocks."""

        return prompt

    @staticmethod
    def build_validation_prompt(code: str) -> str:
        """Build a prompt to validate code quality and suggest improvements."""
        prompt = f"""Analyze this Python code for quality, correctness, and potential issues:

```python
{code}
```

Provide a JSON response with:
{{
    "is_valid": boolean,
    "issues": [list of issues found],
    "severity": "low" | "medium" | "high",
    "improvements": [list of suggested improvements],
    "confidence": float (0.0-1.0, how confident in this code)
}}

Consider:
- Syntax correctness
- Error handling
- Type hints completeness
- Code style and readability
- Performance issues
- Security concerns
- Edge cases handling

Respond ONLY with valid JSON."""

        return prompt

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """Convert procedure name to valid Python function name."""
        # Replace spaces and special chars with underscores
        name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
        # Remove leading digits and underscores
        name = re.sub(r"^[0-9_]+", "", name)
        # Make lowercase
        name = name.lower()
        # Ensure it's not empty
        return name or "procedure"


class ConfidenceScorer:
    """Scores confidence in generated code quality."""

    @staticmethod
    def calculate_confidence(
        code: str,
        procedure: Procedure,
        validation_result: Optional[Dict[str, Any]] = None,
    ) -> float:
        """Calculate confidence score (0.0-1.0) for generated code.

        Factors considered:
        - Syntax validity (AST parsing)
        - Presence of docstring
        - Presence of error handling
        - Type hints coverage
        - Code completeness vs procedure requirements
        - Validation feedback

        Args:
            code: Generated Python code
            procedure: Original procedure definition
            validation_result: Optional validation results from LLM

        Returns:
            Confidence score 0.0-1.0
        """
        confidence = 0.5  # Start with base confidence

        # Check syntax validity
        try:
            import ast

            ast.parse(code)
            confidence += 0.15  # Valid syntax
        except SyntaxError:
            logger.warning("Generated code has syntax errors")
            return 0.0  # Cannot use code with syntax errors

        # Check for docstring
        if '"""' in code or "'''" in code:
            confidence += 0.1

        # Check for error handling
        if "try:" in code and "except" in code:
            confidence += 0.1

        # Check for type hints
        type_hint_count = code.count(":") - code.count("://")  # Rough estimate
        if type_hint_count > 2:
            confidence += 0.1

        # Check for logging
        if "logging" in code or "logger" in code:
            confidence += 0.05

        # Use validation result if available
        if validation_result:
            if isinstance(validation_result, dict):
                validation_confidence = validation_result.get("confidence", 0.0)
                confidence = (confidence + validation_confidence) / 2

        return min(confidence, 1.0)


class ProcedureCodeGenerator:
    """Generates executable code for procedures using LLM.

    Workflow:
    1. Extract procedure context and requirements
    2. Generate code using LLM (Claude or local LLM)
    3. Validate syntax and structure
    4. Calculate confidence score
    5. Refine if confidence is low
    """

    def __init__(self, llm_client: Optional[Any] = None):
        """Initialize code generator.

        Args:
            llm_client: Optional LLM client (Claude, Ollama, etc.)
                       If not provided, uses mock generation
        """
        self.llm_client = llm_client
        self._use_llm = llm_client is not None

        if self._use_llm:
            logger.info("Code generator: LLM-powered generation enabled")
        else:
            logger.info("Code generator: Using mock/fallback generation")

    def generate(self, procedure: Procedure, max_retries: int = 2) -> Tuple[Optional[str], float]:
        """Generate executable code for a procedure.

        Args:
            procedure: Procedure to generate code for
            max_retries: Number of refinement attempts on low confidence

        Returns:
            Tuple of (code_string, confidence_score)
            - code_string: Generated Python code (None if generation failed)
            - confidence_score: 0.0-1.0 confidence in generated code
        """
        try:
            # Generate initial code
            code = self._generate_code(procedure)
            if not code:
                logger.warning(f"Failed to generate code for {procedure.name}")
                return None, 0.0

            # Validate and score
            confidence = ConfidenceScorer.calculate_confidence(code, procedure)
            logger.info(f"Generated code for {procedure.name} with confidence {confidence:.2f}")

            # Refine if confidence is low
            retry_count = 0
            while confidence < 0.7 and retry_count < max_retries:
                logger.info(f"Refining code (attempt {retry_count + 1}/{max_retries})")
                code = self._refine_code(code, procedure)
                if code:
                    confidence = ConfidenceScorer.calculate_confidence(code, procedure)
                retry_count += 1

            return code, confidence

        except Exception as e:
            logger.error(f"Error generating code for {procedure.name}: {e}")
            return None, 0.0

    def _generate_code(self, procedure: Procedure) -> Optional[str]:
        """Generate code from procedure using LLM or fallback."""
        if self._use_llm:
            return self._generate_with_llm(procedure)
        else:
            return self._generate_fallback(procedure)

    def _generate_with_llm(self, procedure: Procedure) -> Optional[str]:
        """Generate code using LLM client."""
        try:
            prompt = CodeGenerationPrompt.build_code_generation_prompt(procedure)

            # Support different LLM client interfaces
            if hasattr(self.llm_client, "generate"):
                response = self.llm_client.generate(prompt)
            elif hasattr(self.llm_client, "complete"):
                response = self.llm_client.complete(prompt)
            elif hasattr(self.llm_client, "messages"):
                response = self.llm_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1000,
                    messages=[{"role": "user", "content": prompt}],
                )
                if hasattr(response, "content"):
                    response = response.content[0].text
            else:
                logger.warning("LLM client interface not recognized")
                return None

            # Extract code from response
            code = self._extract_code(response)
            return code

        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return None

    def _generate_fallback(self, procedure: Procedure) -> str:
        """Generate code using heuristic/template approach."""
        name = CodeGenerationPrompt._sanitize_name(procedure.name)
        category = procedure.category

        # Build basic function stub
        code_parts = [
            f'def {name}(**kwargs):\n    """',
            f'    {procedure.description or "Execute " + procedure.name}.',
            "",
            "    Args:",
            "        **kwargs: Procedure parameters",
            "",
            "    Returns:",
            "        dict: Result of procedure execution",
            '    """',
            "    import logging",
            "    logger = logging.getLogger(__name__)",
            "",
            '    logger.info(f"Executing {name} with {kwargs}")',
            "    ",
            "    try:",
            "        # TODO: Implement procedure logic",
            f"        # Category: {category}",
        ]

        # Add category-specific stub
        if category == "git":
            code_parts.extend(
                [
                    "        import subprocess",
                    '        result = subprocess.run(["git", "status"], capture_output=True)',
                    "        return {",
                    '            "success": result.returncode == 0,',
                    '            "output": result.stdout.decode(),',
                    "        }",
                ]
            )
        elif category == "testing":
            code_parts.extend(
                [
                    "        # Run tests",
                    "        results = []",
                    "        return {",
                    '            "passed": len(results),',
                    '            "results": results,',
                    "        }",
                ]
            )
        else:
            code_parts.extend(
                [
                    "        result = {}",
                    "        return {",
                    '            "success": True,',
                    '            "result": result,',
                    "        }",
                ]
            )

        code_parts.extend(
            [
                "    except Exception as e:",
                "        logger.error(f'Error in {name}: {e}')",
                "        return {",
                '            "success": False,',
                '            "error": str(e),',
                "        }",
            ]
        )

        return "\n".join(code_parts)

    def _refine_code(self, code: str, procedure: Procedure) -> str:
        """Refine code based on quality issues."""
        if not self._use_llm:
            return code

        try:
            feedback = f"Improve code quality, error handling, and robustness. Ensure it properly implements {procedure.name}."
            prompt = CodeGenerationPrompt.build_refinement_prompt(code, feedback)

            if hasattr(self.llm_client, "generate"):
                response = self.llm_client.generate(prompt)
            elif hasattr(self.llm_client, "complete"):
                response = self.llm_client.complete(prompt)
            else:
                return code

            refined_code = self._extract_code(response)
            return refined_code if refined_code else code

        except Exception as e:
            logger.error(f"Code refinement error: {e}")
            return code

    @staticmethod
    def _extract_code(response: str) -> Optional[str]:
        """Extract Python code from LLM response."""
        # Try to extract from markdown code blocks first
        pattern = r"```(?:python)?\n(.*?)```"
        match = re.search(pattern, response, re.DOTALL)
        if match:
            return match.group(1).strip()

        # If no code blocks, return the whole response (assume it's code)
        if "def " in response:
            return response.strip()

        return None
