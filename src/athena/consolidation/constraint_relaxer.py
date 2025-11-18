"""
Constraint relaxer for generating procedure variants.

Systematically violates constraints to explore adjacent possibilities,
respecting dependency relationships to ensure safety.
"""

from typing import List, Optional, Dict
from dataclasses import dataclass
import logging
import re

from .dependency_analyzer import DependencyGraph, ProcedureDependencyAnalyzer
from .openrouter_client import OpenRouterClient, DREAM_MODELS_CONFIG

logger = logging.getLogger(__name__)


@dataclass
class DreamProcedure:
    """A generated dream procedure variant."""

    name: str
    base_procedure_id: int
    base_procedure_name: str
    dream_type: str  # "constraint_relaxation", "parameter_variation", etc.
    code: str
    model_used: str
    reasoning: str  # Why this variant was generated
    generated_description: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage/serialization."""
        return {
            "name": self.name,
            "base_procedure_id": self.base_procedure_id,
            "base_procedure_name": self.base_procedure_name,
            "dream_type": self.dream_type,
            "code": self.code,
            "model_used": self.model_used,
            "reasoning": self.reasoning,
            "generated_description": self.generated_description,
        }


class ConstraintRelaxer:
    """
    Generate procedure variants by systematically violating constraints.

    Strategy:
    1. Analyze dependencies using AST
    2. Identify safe transformation opportunities
    3. Use DeepSeek V3.1 to generate creative variants
    4. Validate variants don't violate hard constraints
    """

    def __init__(self, client: OpenRouterClient):
        self.client = client
        self.config = DREAM_MODELS_CONFIG["constraint_relaxation"]

    async def generate_variants(
        self,
        procedure_id: int,
        procedure_name: str,
        procedure_code: str,
        depth: str = "moderate",  # "light", "moderate", "deep"
    ) -> List[DreamProcedure]:
        """
        Generate constraint-relaxation variants of a procedure.

        Args:
            procedure_id: ID of base procedure
            procedure_name: Name of base procedure
            procedure_code: Python code of procedure
            depth: How aggressive to be ("light" = 5 variants, "moderate" = 15, "deep" = 30)

        Returns:
            List of DreamProcedure variants
        """
        # Analyze dependencies first
        analyzer = ProcedureDependencyAnalyzer(procedure_id, procedure_code)
        dep_graph = analyzer.analyze()

        variant_count = {"light": 5, "moderate": 15, "deep": 30}.get(depth, 15)

        # Build prompt for DeepSeek
        prompt = self._build_generation_prompt(
            procedure_name, procedure_code, dep_graph, variant_count
        )

        try:
            response = await self.client.generate(
                model=self.config["primary"],
                prompt=prompt,
                system=self._get_system_prompt(),
                max_tokens=self.config["max_tokens"],
                temperature=self.config["temperature"],
                top_p=self.config["top_p"],
            )

            # Parse response to extract variants
            variants = self._parse_response(
                response["content"], procedure_id, procedure_name, "constraint_relaxation"
            )

            logger.info(
                f"Generated {len(variants)} constraint-relaxation variants "
                f"for procedure {procedure_name}"
            )

            return variants

        except Exception as e:
            logger.error(
                f"Error generating constraint-relaxation variants for {procedure_name}: {e}"
            )
            return []

    def _get_system_prompt(self) -> str:
        """Get system prompt for constraint relaxation."""
        return """You are an AI system that generates creative procedure variants by
systematically violating constraints and exploring adjacent possibilities.

Your goal is to generate safe, working Python code that:
1. Violates at least one assumption from the original procedure
2. Still makes logical sense and could work in practice
3. Respects hard dependencies (don't break data flow)
4. Explores different execution patterns (reordering, conditionals, parallelization)

For each variant, explain WHY the violation makes sense and WHAT assumption it challenges.

Generate code that is syntactically valid and executable."""

    def _build_generation_prompt(
        self,
        procedure_name: str,
        procedure_code: str,
        dep_graph: DependencyGraph,
        variant_count: int,
    ) -> str:
        """Build prompt for variant generation."""
        # Identify key constraints
        constraints = self._identify_constraints(procedure_code, dep_graph)

        # Identify reorderable steps
        reorderable_steps = self._find_reorderable_steps(dep_graph)

        # Identify independent steps that could parallelize
        parallelizable_groups = dep_graph.find_independent_steps()

        prompt = f"""I have a Python procedure and need to generate {variant_count} creative variants.

ORIGINAL PROCEDURE:
```python
{procedure_code}
```

CONSTRAINT ANALYSIS:
- Procedure name: {procedure_name}
- Total steps: {len(dep_graph.steps)}
- Has loops: {dep_graph.has_loops}
- Has conditionals: {dep_graph.has_conditionals}
- Has side effects: {dep_graph.has_side_effects}

KEY CONSTRAINTS (Can be violated):
{chr(10).join(f"- {c}" for c in constraints[:5])}

SAFE REORDERINGS (steps that CAN be safely reordered):
{chr(10).join(f"- {s}" for s in reorderable_steps[:5]) if reorderable_steps else "- (None identified)"}

PARALLELIZABLE GROUPS (steps that could run simultaneously):
{chr(10).join(f"- {g}" for g in parallelizable_groups[:3]) if parallelizable_groups else "- (None identified)"}

GENERATION STRATEGY:
1. Reorder steps where safe (challenge assumption of sequential execution)
2. Add conditional execution where applicable (challenge assumption of always running)
3. Parallelize independent steps (challenge sequential pattern)
4. Modify parameters/timeouts (challenge specific values)
5. Combine techniques (challenge multiple assumptions simultaneously)

For EACH variant, provide:
1. A brief name/description (1-2 lines)
2. The complete Python code
3. The assumption violated (1 line)
4. Why this could be useful (1-2 lines)

Generate {variant_count} variants total. Be creative but practical."""

        return prompt

    def _identify_constraints(self, code: str, dep_graph: DependencyGraph) -> List[str]:
        """Identify key constraints in the procedure."""
        constraints = []

        # Sequential execution
        if len(dep_graph.steps) > 1:
            constraints.append("Steps execute sequentially in defined order")

        # Required side effects
        if dep_graph.has_side_effects:
            constraints.append("All operations are executed (none can be skipped)")

        # Specific error handling
        if "try" in code or "except" in code:
            constraints.append("Error handling path must be followed exactly")

        # Specific timeouts/delays
        if "sleep" in code or "timeout" in code or "wait" in code:
            constraints.append("Specific timing values are fixed")

        # Subprocess calls
        if "subprocess" in code or "os.system" in code:
            constraints.append("External commands must run in specific order")

        return constraints

    def _find_reorderable_steps(self, dep_graph: DependencyGraph) -> List[str]:
        """Find steps that could be safely reordered."""
        reorderable = []

        for i, step_a in enumerate(dep_graph.steps):
            for j, step_b in enumerate(dep_graph.steps[i + 1 :], start=i + 1):
                if dep_graph.can_reorder(i, j):
                    reorderable.append(f"Step {i} ↔ Step {j} (swap {step_a.code[:30]}... with ...)")

        return reorderable[:5]  # Return top 5

    def _parse_response(
        self, response: str, procedure_id: int, procedure_name: str, dream_type: str
    ) -> List[DreamProcedure]:
        """Parse DeepSeek response to extract variant code."""
        variants = []

        # Split by variant markers (numbered sections, code blocks, etc.)
        # This is a heuristic parser - adapt to actual DeepSeek output format
        sections = re.split(r"(?:^|\n)(?:Variant\s+\d+|^#{1,3}\s+(?:Variant|Dream))", response)

        for i, section in enumerate(sections[1:], 1):  # Skip first empty section
            variant = self._extract_variant_from_section(
                section, procedure_id, procedure_name, dream_type
            )

            if variant:
                variants.append(variant)

        return variants

    def _extract_variant_from_section(
        self, section: str, procedure_id: int, procedure_name: str, dream_type: str
    ) -> Optional[DreamProcedure]:
        """Extract a single variant from a response section."""
        # Extract Python code block
        code_match = re.search(r"```python\n(.*?)\n```", section, re.DOTALL)

        if not code_match:
            code_match = re.search(r"```\n(.*?)\n```", section, re.DOTALL)

        if not code_match:
            # Try to find raw code (lines starting with def or class)
            code_match = re.search(
                r"^(?:def |class |async def )(.*?)(?=\n(?:def|class|Variant|Dream|$))",
                section,
                re.MULTILINE | re.DOTALL,
            )

        if not code_match:
            return None

        code = code_match.group(1).strip()

        # Ensure code is syntactically valid
        try:
            compile(code, "<string>", "exec")
        except SyntaxError:
            logger.warning("Generated code has syntax error, skipping variant")
            return None

        # Extract description
        desc_match = re.search(r"^(.{1,100})", section.strip())
        description = desc_match.group(1) if desc_match else "Generated variant"

        # Extract assumption violated
        assumption_match = re.search(
            r"(?:assumption|constraint|violat)[^:]*?:\s*(.{1,150})", section, re.IGNORECASE
        )
        assumption = assumption_match.group(1) if assumption_match else "Unspecified"

        return DreamProcedure(
            name=f"{procedure_name}_v{self._generate_variant_id()}",
            base_procedure_id=procedure_id,
            base_procedure_name=procedure_name,
            dream_type=dream_type,
            code=code,
            model_used="deepseek/deepseek-chat-v3.1:free",
            reasoning=f"Relaxed: {assumption}",
            generated_description=description,
        )

    def _generate_variant_id(self) -> str:
        """Generate a unique variant ID."""
        import uuid

        return str(uuid.uuid4())[:8]
