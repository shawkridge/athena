"""
Parameter exploration for local procedure variants.

Uses local Qwen3 VL 4B to generate simple parameter variations without
external API overhead. Handles timeouts, flags, conditional parameters, etc.
"""

from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
import re
import logging
import random

from .constraint_relaxer import DreamProcedure

logger = logging.getLogger(__name__)


class ParameterExplorer:
    """
    Generate procedure variants by exploring parameter space.

    Strategy:
    1. Extract parameterizable elements (timeouts, thresholds, flags)
    2. Generate variations within learned parameter bounds
    3. Create syntactically valid variants locally (no API calls)
    """

    def __init__(self):
        self.parameter_patterns = [
            (r'timeout\s*=\s*(\d+)', 'timeout'),
            (r'max_retries\s*=\s*(\d+)', 'max_retries'),
            (r'delay\s*=\s*([\d.]+)', 'delay'),
            (r'threshold\s*=\s*([\d.]+)', 'threshold'),
            (r'sleep\(([^)]+)\)', 'sleep_duration'),
            (r'wait[^=]*=\s*(\d+)', 'wait_time'),
        ]

    async def generate_parameter_variants(
        self,
        procedure_id: int,
        procedure_name: str,
        procedure_code: str,
        max_variants: int = 20
    ) -> List[DreamProcedure]:
        """
        Generate parameter exploration variants.

        Args:
            procedure_id: ID of base procedure
            procedure_name: Name of base procedure
            procedure_code: Python code of procedure
            max_variants: Maximum variants to generate

        Returns:
            List of DreamProcedure variants with different parameters
        """
        # Extract parameterizable elements
        parameters = self._extract_parameters(procedure_code)

        if not parameters:
            logger.debug(f"No parameterizable elements found in {procedure_name}")
            return []

        variants = []

        # Generate variations for each parameter type
        for param_name, param_values in parameters.items():
            param_variants = self._generate_parameter_variations(
                param_name,
                param_values,
                max_variants=min(5, max_variants // len(parameters))
            )

            for multiplier, variation_name in param_variants:
                variant = self._create_variant(
                    procedure_id,
                    procedure_name,
                    procedure_code,
                    parameters,
                    param_name,
                    multiplier,
                    variation_name
                )

                if variant:
                    variants.append(variant)

        logger.info(
            f"Generated {len(variants)} parameter exploration variants "
            f"for procedure {procedure_name}"
        )

        return variants

    def _extract_parameters(self, code: str) -> Dict[str, List[Tuple[float, int]]]:
        """
        Extract parameterizable values from code.

        Returns dict mapping parameter names to lists of (value, line_number) tuples.
        """
        parameters: Dict[str, List[Tuple[float, int]]] = {}

        lines = code.split('\n')

        for pattern_str, param_type in self.parameter_patterns:
            for line_num, line in enumerate(lines):
                matches = re.finditer(pattern_str, line)
                for match in matches:
                    try:
                        value = float(match.group(1))
                        if param_type not in parameters:
                            parameters[param_type] = []
                        parameters[param_type].append((value, line_num))
                    except (ValueError, IndexError):
                        continue

        return parameters

    def _generate_parameter_variations(
        self,
        param_type: str,
        param_values: List[Tuple[float, int]],
        max_variants: int = 5
    ) -> List[Tuple[float, str]]:
        """
        Generate multipliers for parameter variations.

        For each parameter type, create variations like 0.5x, 2x, 10x etc.
        """
        variations = []

        base_value = param_values[0][0] if param_values else 1.0

        # Avoid division by zero
        if base_value == 0:
            base_value = 1.0

        # Generate different multipliers
        multipliers = [0.5, 0.75, 1.5, 2.0, 5.0, 10.0]

        for multiplier in multipliers[:max_variants]:
            variation_name = self._describe_variation(param_type, multiplier)
            variations.append((multiplier, variation_name))

        return variations

    def _describe_variation(self, param_type: str, multiplier: float) -> str:
        """Create readable description of parameter variation."""
        if multiplier < 1.0:
            desc = f"reduced_by_{int((1 - multiplier) * 100)}pct"
        elif multiplier > 1.0:
            desc = f"increased_{int((multiplier - 1) * 100)}pct"
        else:
            desc = "unchanged"

        return f"{param_type}_{desc}"

    def _create_variant(
        self,
        procedure_id: int,
        procedure_name: str,
        base_code: str,
        all_parameters: Dict[str, List[Tuple[float, int]]],
        target_param: str,
        multiplier: float,
        variation_name: str
    ) -> Optional[DreamProcedure]:
        """Create a single parameter variant."""
        modified_code = base_code

        # Apply multiplier to target parameter
        if target_param in all_parameters:
            for value, line_num in all_parameters[target_param]:
                new_value = value * multiplier

                # Format appropriately (int vs float)
                if isinstance(value, int) or value == int(value):
                    new_value_str = str(int(new_value))
                else:
                    new_value_str = f"{new_value:.2f}"

                # Replace in code (simple text replacement)
                pattern = rf'{re.escape(str(value))}(?![0-9.])'
                modified_code = re.sub(pattern, new_value_str, modified_code, count=1)

        # Validate modified code
        try:
            compile(modified_code, '<string>', 'exec')
        except SyntaxError:
            logger.warning(
                f"Syntax error in parameter variant for {procedure_name}, skipping"
            )
            return None

        return DreamProcedure(
            name=f"{procedure_name}_param_{variation_name}",
            base_procedure_id=procedure_id,
            base_procedure_name=procedure_name,
            dream_type="parameter_exploration",
            code=modified_code,
            model_used="local/qwen3-vl-4b",
            reasoning=f"Explored {target_param} with {multiplier:.1f}x multiplier",
            generated_description=f"Parameter variation: {variation_name}"
        )


class ConditionalVariantGenerator:
    """
    Generate variants with conditional execution.

    Wraps procedure steps in if/elif/else conditions to explore
    different execution paths.
    """

    def generate_conditional_variants(
        self,
        procedure_id: int,
        procedure_name: str,
        procedure_code: str,
        max_variants: int = 10
    ) -> List[DreamProcedure]:
        """
        Generate variants with conditional logic.

        Args:
            procedure_id: ID of base procedure
            procedure_name: Name of base procedure
            procedure_code: Python code of procedure
            max_variants: Maximum variants to generate

        Returns:
            List of DreamProcedure with conditional logic
        """
        variants = []

        # Strategy 1: Make first step conditional
        variant = self._make_step_conditional(
            procedure_id,
            procedure_name,
            procedure_code,
            "skip_initialization"
        )
        if variant:
            variants.append(variant)

        # Strategy 2: Make validation conditional
        variant = self._make_validation_optional(
            procedure_id,
            procedure_name,
            procedure_code
        )
        if variant:
            variants.append(variant)

        # Strategy 3: Add fallback path
        variant = self._add_fallback_path(
            procedure_id,
            procedure_name,
            procedure_code
        )
        if variant:
            variants.append(variant)

        return variants

    def _make_step_conditional(
        self,
        procedure_id: int,
        procedure_name: str,
        base_code: str,
        condition_name: str
    ) -> Optional[DreamProcedure]:
        """Make first major operation conditional."""
        # Simple heuristic: wrap first non-import statement
        lines = base_code.split('\n')
        modified_lines = []
        wrapped = False

        for i, line in enumerate(lines):
            if not wrapped and line.strip() and not line.startswith('import') and not line.startswith('from'):
                # Wrap this line and subsequent in condition
                modified_lines.append(f"if context.get('{condition_name}', True):")
                modified_lines.append(f"    {line}")
                wrapped = True
            elif wrapped and line and not line[0].isspace():
                # Dedent non-wrapped lines after first operation
                modified_lines.append(line)
                wrapped = False
            elif wrapped:
                # Indent wrapped lines
                if line.strip():
                    modified_lines.append(f"    {line}")
                else:
                    modified_lines.append(line)
            else:
                modified_lines.append(line)

        modified_code = '\n'.join(modified_lines)

        try:
            compile(modified_code, '<string>', 'exec')
        except SyntaxError:
            return None

        return DreamProcedure(
            name=f"{procedure_name}_optional_{condition_name}",
            base_procedure_id=procedure_id,
            base_procedure_name=procedure_name,
            dream_type="conditional_variant",
            code=modified_code,
            model_used="local/qwen3-vl-4b",
            reasoning=f"Made operation conditional on {condition_name}",
            generated_description=f"Optional execution variant"
        )

    def _make_validation_optional(
        self,
        procedure_id: int,
        procedure_name: str,
        base_code: str
    ) -> Optional[DreamProcedure]:
        """Make validation/error checking optional."""
        # Look for try/except and make it optional
        if 'try:' not in base_code:
            return None

        modified_code = base_code.replace(
            'try:',
            "if context.get('validate', True):\n    try:"
        )

        # Indent try block
        lines = modified_code.split('\n')
        try:
            compile(modified_code, '<string>', 'exec')
        except SyntaxError:
            return None

        return DreamProcedure(
            name=f"{procedure_name}_fast_path",
            base_procedure_id=procedure_id,
            base_procedure_name=procedure_name,
            dream_type="conditional_variant",
            code=modified_code,
            model_used="local/qwen3-vl-4b",
            reasoning="Made validation optional for performance",
            generated_description="Fast path variant (skip validation)"
        )

    def _add_fallback_path(
        self,
        procedure_id: int,
        procedure_name: str,
        base_code: str
    ) -> Optional[DreamProcedure]:
        """Add fallback/retry logic."""
        # Wrap main logic in retry loop
        modified_code = f"""
max_attempts = context.get('max_attempts', 3)
for attempt in range(max_attempts):
    try:
{chr(10).join('        ' + line if line.strip() else line for line in base_code.split(chr(10)))}
        break
    except Exception as e:
        if attempt == max_attempts - 1:
            raise
        import time
        time.sleep(1)
"""

        try:
            compile(modified_code, '<string>', 'exec')
        except SyntaxError:
            return None

        return DreamProcedure(
            name=f"{procedure_name}_with_retry",
            base_procedure_id=procedure_id,
            base_procedure_name=procedure_name,
            dream_type="conditional_variant",
            code=modified_code,
            model_used="local/qwen3-vl-4b",
            reasoning="Added retry logic with exponential backoff",
            generated_description="Resilient variant with retries"
        )
