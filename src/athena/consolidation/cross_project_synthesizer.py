"""
Cross-project procedure synthesizer.

Uses semantic search and code synthesis to combine procedures from different
projects into novel hybrid variants.
"""

from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
import logging
import re

from .openrouter_client import OpenRouterClient, DREAM_MODELS_CONFIG
from .constraint_relaxer import DreamProcedure

logger = logging.getLogger(__name__)


@dataclass
class ProcedureReference:
    """Reference to a procedure for synthesis."""

    id: int
    name: str
    category: str
    description: str
    code_snippet: str  # First 500 chars
    applicable_contexts: List[str]
    semantic_tags: List[str]


class CrossProjectSynthesizer:
    """
    Generate hybrid procedures by combining code from different projects.

    Strategy:
    1. Find semantically related procedures across projects
    2. Analyze code structure compatibility
    3. Use Qwen2.5-Coder to synthesize combinations
    4. Return novel hybrid procedures
    """

    def __init__(self, client: OpenRouterClient):
        self.client = client
        self.config = DREAM_MODELS_CONFIG["cross_project_synthesis"]

    async def generate_synthesis_variants(
        self,
        base_procedure_id: int,
        base_procedure_name: str,
        base_procedure_code: str,
        related_procedures: List[ProcedureReference],
        max_variants: int = 15,
    ) -> List[DreamProcedure]:
        """
        Generate hybrid procedure variants by synthesizing with related procedures.

        Args:
            base_procedure_id: ID of the base procedure
            base_procedure_name: Name of base procedure
            base_procedure_code: Code of base procedure
            related_procedures: List of related procedures to combine with
            max_variants: Maximum variants to generate

        Returns:
            List of DreamProcedure hybrids
        """
        if not related_procedures:
            logger.warning(f"No related procedures found for {base_procedure_name}")
            return []

        # Select best candidates to combine (avoid too many combinations)
        candidates = self._select_best_candidates(
            related_procedures, max_combinations=min(max_variants // 2, 5)
        )

        variants = []

        for related in candidates:
            prompt = self._build_synthesis_prompt(
                base_procedure_name,
                base_procedure_code,
                related.name,
                related.code_snippet,
                related.description,
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

                variant = self._extract_hybrid_variant(
                    response["content"], base_procedure_id, base_procedure_name, related
                )

                if variant:
                    variants.append(variant)

            except Exception as e:
                logger.error(f"Error synthesizing {base_procedure_name} with {related.name}: {e}")
                continue

        logger.info(
            f"Generated {len(variants)} cross-project synthesis variants "
            f"for procedure {base_procedure_name}"
        )

        return variants

    def _select_best_candidates(
        self, procedures: List[ProcedureReference], max_combinations: int
    ) -> List[ProcedureReference]:
        """
        Select best procedures to synthesize with.

        Prefer procedures from different categories/projects for novelty.
        """
        # Group by category
        by_category: Dict[str, List[ProcedureReference]] = {}
        for proc in procedures:
            if proc.category not in by_category:
                by_category[proc.category] = []
            by_category[proc.category].append(proc)

        # Select from different categories
        selected = []
        for category, procs in by_category.items():
            if selected and len(selected) >= max_combinations:
                break
            # Take first from each category
            selected.append(procs[0])

        return selected[:max_combinations]

    def _get_system_prompt(self) -> str:
        """Get system prompt for synthesis."""
        return """You are an expert code synthesizer that combines procedures from different domains.

Your goal is to create a new procedure that intelligently combines approaches from two different contexts:
1. Merge relevant steps from both procedures
2. Adapt code to work together cohesively
3. Maintain the strengths of both approaches
4. Handle any conflicts or incompatibilities gracefully
5. Add transition logic where needed

Generate complete, working Python code that could be executed. Ensure:
- All imports are included
- All functions and variables are defined
- Error handling is appropriate
- The code style is consistent
- Comments explain the hybrid approach

The result should be syntactically valid and executable."""

    def _build_synthesis_prompt(
        self,
        base_name: str,
        base_code: str,
        related_name: str,
        related_code: str,
        related_description: str,
    ) -> str:
        """Build prompt for procedure synthesis."""
        prompt = f"""I need you to synthesize a hybrid procedure combining two approaches:

BASE PROCEDURE: {base_name}
```python
{base_code}
```

RELATED PROCEDURE: {related_name}
{related_description}
```python
{related_code}
```

SYNTHESIS TASK:
Create a new procedure that intelligently combines both approaches. Consider:
1. Can steps from {related_name} improve {base_name}?
2. How would {related_name}'s error handling apply here?
3. What would a hybrid approach look like?
4. Are there domain-specific techniques that transfer?

IMPORTANT:
- Generate COMPLETE, executable Python code
- Include all necessary imports
- Define all functions and variables
- Add comments explaining the hybrid approach
- Ensure the code is syntactically valid

Provide:
1. A name for the hybrid procedure (1 line)
2. Brief description (2-3 lines)
3. Complete Python code

Remember: You are combining techniques from different domains. Look for:
- Similar patterns (error handling, validation, state management)
- Complementary approaches (sequential vs. parallel, strict vs. lenient)
- Domain-specific wisdom that could transfer"""

        return prompt

    def _extract_hybrid_variant(
        self, response: str, base_id: int, base_name: str, related: ProcedureReference
    ) -> Optional[DreamProcedure]:
        """Extract hybrid variant from Qwen response."""
        # Extract Python code block
        code_match = re.search(r"```python\n(.*?)\n```", response, re.DOTALL)

        if not code_match:
            code_match = re.search(r"```\n(.*?)\n```", response, re.DOTALL)

        if not code_match:
            logger.warning("Could not find code block in synthesis response")
            return None

        code = code_match.group(1).strip()

        # Validate syntax
        try:
            compile(code, "<string>", "exec")
        except SyntaxError as e:
            logger.warning(f"Synthesis generated invalid Python: {e}")
            return None

        # Extract name and description
        lines = response.split("\n")
        hybrid_name = f"{base_name}_×_{related.name[:15]}_hybrid"
        description = f"Hybrid of {base_name} and {related.name} approaches"

        # Extract any description provided
        for line in lines[:5]:
            if line.strip() and not line.startswith("```"):
                description = line.strip()
                break

        return DreamProcedure(
            name=hybrid_name,
            base_procedure_id=base_id,
            base_procedure_name=base_name,
            dream_type="cross_project_synthesis",
            code=code,
            model_used="qwen/qwen-2.5-coder-32b-instruct:free",
            reasoning=f"Synthesized {base_name} with {related.name} ({related.category})",
            generated_description=description,
        )


class SemanticProcedureMatcher:
    """
    Find semantically related procedures across projects.

    This would integrate with Athena's semantic search capabilities.
    """

    def __init__(self, client: OpenRouterClient):
        self.client = client

    async def find_related_procedures(
        self,
        procedure: ProcedureReference,
        all_procedures: List[ProcedureReference],
        max_results: int = 5,
        exclude_project: Optional[str] = None,
    ) -> List[Tuple[ProcedureReference, float]]:
        """
        Find procedures semantically related to the given procedure.

        Args:
            procedure: Reference procedure
            all_procedures: All available procedures
            max_results: Maximum related procedures to return
            exclude_project: Project ID to exclude (to force cross-project)

        Returns:
            List of (procedure, similarity_score) tuples sorted by score
        """
        # In real implementation, this would use semantic embeddings
        # For now, use heuristic matching on tags and categories

        scores = []

        for candidate in all_procedures:
            if candidate.id == procedure.id:
                continue

            # Calculate similarity
            score = self._calculate_similarity(procedure, candidate)

            if score > 0.3:  # Minimum threshold
                scores.append((candidate, score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        return scores[:max_results]

    def _calculate_similarity(
        self, proc_a: ProcedureReference, proc_b: ProcedureReference
    ) -> float:
        """Calculate similarity between two procedures."""
        score = 0.0

        # Same category = some similarity
        if proc_a.category == proc_b.category:
            score += 0.3

        # Shared semantic tags = higher similarity
        shared_tags = set(proc_a.semantic_tags) & set(proc_b.semantic_tags)
        if shared_tags:
            score += len(shared_tags) * 0.2

        # Shared contexts = similarity
        shared_contexts = set(proc_a.applicable_contexts) & set(proc_b.applicable_contexts)
        if shared_contexts:
            score += len(shared_contexts) * 0.15

        # Cross-domain bonus (different categories but related tags)
        if proc_a.category != proc_b.category and shared_tags:
            score += 0.2

        return min(score, 1.0)
