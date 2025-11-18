"""
Dream orchestrator for speculative procedure generation.

Coordinates parallel dream generation using multiple specialized models:
- DeepSeek V3.1 for constraint relaxation and semantic matching
- Qwen2.5-Coder 32B for cross-project synthesis
- Local Qwen3 VL 4B for parameter exploration
"""

import asyncio
from typing import List, Optional, Tuple
from dataclasses import dataclass
import logging

from .openrouter_client import OpenRouterClient
from .constraint_relaxer import ConstraintRelaxer, DreamProcedure
from .cross_project_synthesizer import CrossProjectSynthesizer, ProcedureReference
from .parameter_explorer import ParameterExplorer, ConditionalVariantGenerator

logger = logging.getLogger(__name__)


@dataclass
class DreamGenerationConfig:
    """Configuration for dream generation."""

    strategy: str = "balanced"  # "light", "balanced", "deep"
    max_variants_per_category: int = 15
    constraint_relaxation_enabled: bool = True
    cross_project_synthesis_enabled: bool = True
    parameter_exploration_enabled: bool = True
    conditional_variants_enabled: bool = True
    parallel_generation: bool = True

    @classmethod
    def from_strategy(cls, strategy: str = "balanced") -> "DreamGenerationConfig":
        """Create config from strategy name."""
        configs = {
            "light": cls(
                strategy="light",
                max_variants_per_category=5,
                constraint_relaxation_enabled=True,
                cross_project_synthesis_enabled=False,
                parameter_exploration_enabled=True,
                conditional_variants_enabled=False,
            ),
            "balanced": cls(
                strategy="balanced",
                max_variants_per_category=15,
                constraint_relaxation_enabled=True,
                cross_project_synthesis_enabled=True,
                parameter_exploration_enabled=True,
                conditional_variants_enabled=True,
            ),
            "deep": cls(
                strategy="deep",
                max_variants_per_category=30,
                constraint_relaxation_enabled=True,
                cross_project_synthesis_enabled=True,
                parameter_exploration_enabled=True,
                conditional_variants_enabled=True,
            ),
        }
        return configs.get(strategy, cls())


class DreamGenerator:
    """
    Orchestrator for speculative procedure generation.

    Generates dream variants through:
    1. Constraint relaxation (DeepSeek V3.1)
    2. Cross-project synthesis (Qwen2.5-Coder 32B)
    3. Parameter exploration (Local Qwen3)
    4. Conditional variants (Local)
    """

    def __init__(self, client: Optional[OpenRouterClient] = None):
        """Initialize dream generator."""
        self.client = client or OpenRouterClient.from_env()
        self.constraint_relaxer = ConstraintRelaxer(self.client)
        self.cross_project_synthesizer = CrossProjectSynthesizer(self.client)
        self.parameter_explorer = ParameterExplorer()
        self.conditional_generator = ConditionalVariantGenerator()

    async def generate_dreams(
        self,
        procedure_id: int,
        procedure_name: str,
        procedure_code: str,
        related_procedures: Optional[List[ProcedureReference]] = None,
        config: Optional[DreamGenerationConfig] = None,
    ) -> List[DreamProcedure]:
        """
        Generate dream variants for a procedure.

        Args:
            procedure_id: ID of the procedure
            procedure_name: Name of the procedure
            procedure_code: Python code of the procedure
            related_procedures: Optional list of related procedures for synthesis
            config: Dream generation configuration

        Returns:
            List of generated dream procedure variants
        """
        if config is None:
            config = DreamGenerationConfig.from_strategy("balanced")

        logger.info(
            f"Starting dream generation for {procedure_name} " f"(strategy={config.strategy})"
        )

        all_dreams = []
        dreams_by_type = {
            "constraint_relaxation": [],
            "cross_project_synthesis": [],
            "parameter_exploration": [],
            "conditional_variants": [],
        }

        if config.parallel_generation:
            # Generate all dream types in parallel
            tasks = []

            if config.constraint_relaxation_enabled:
                tasks.append(
                    self._generate_constraint_relaxation(
                        procedure_id, procedure_name, procedure_code, config
                    )
                )

            if config.cross_project_synthesis_enabled and related_procedures:
                tasks.append(
                    self._generate_cross_project(
                        procedure_id, procedure_name, procedure_code, related_procedures, config
                    )
                )

            if config.parameter_exploration_enabled:
                tasks.append(
                    self._generate_parameter_variants(
                        procedure_id, procedure_name, procedure_code, config
                    )
                )

            if config.conditional_variants_enabled:
                tasks.append(
                    self._generate_conditional_variants(
                        procedure_id, procedure_name, procedure_code, config
                    )
                )

            # Run all in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Error during dream generation: {result}")
                elif isinstance(result, tuple):
                    dream_type, dreams = result
                    dreams_by_type[dream_type] = dreams
                    all_dreams.extend(dreams)

        else:
            # Sequential generation (for debugging)
            if config.constraint_relaxation_enabled:
                dream_type, dreams = await self._generate_constraint_relaxation(
                    procedure_id, procedure_name, procedure_code, config
                )
                dreams_by_type[dream_type] = dreams
                all_dreams.extend(dreams)

            if config.cross_project_synthesis_enabled and related_procedures:
                dream_type, dreams = await self._generate_cross_project(
                    procedure_id, procedure_name, procedure_code, related_procedures, config
                )
                dreams_by_type[dream_type] = dreams
                all_dreams.extend(dreams)

            if config.parameter_exploration_enabled:
                dream_type, dreams = await self._generate_parameter_variants(
                    procedure_id, procedure_name, procedure_code, config
                )
                dreams_by_type[dream_type] = dreams
                all_dreams.extend(dreams)

            if config.conditional_variants_enabled:
                dream_type, dreams = await self._generate_conditional_variants(
                    procedure_id, procedure_name, procedure_code, config
                )
                dreams_by_type[dream_type] = dreams
                all_dreams.extend(dreams)

        # Log summary
        logger.info(f"Generated {len(all_dreams)} total dreams for {procedure_name}:")
        for dream_type, dreams in dreams_by_type.items():
            if dreams:
                logger.info(f"  - {len(dreams)} {dream_type} variants")

        return all_dreams

    async def _generate_constraint_relaxation(
        self,
        procedure_id: int,
        procedure_name: str,
        procedure_code: str,
        config: DreamGenerationConfig,
    ) -> Tuple[str, List[DreamProcedure]]:
        """Generate constraint relaxation variants."""
        try:
            depth_map = {"light": "light", "balanced": "moderate", "deep": "deep"}
            depth = depth_map.get(config.strategy, "moderate")

            variants = await self.constraint_relaxer.generate_variants(
                procedure_id, procedure_name, procedure_code, depth=depth
            )

            return "constraint_relaxation", variants

        except Exception as e:
            logger.error(f"Error in constraint relaxation: {e}")
            return "constraint_relaxation", []

    async def _generate_cross_project(
        self,
        procedure_id: int,
        procedure_name: str,
        procedure_code: str,
        related_procedures: List[ProcedureReference],
        config: DreamGenerationConfig,
    ) -> Tuple[str, List[DreamProcedure]]:
        """Generate cross-project synthesis variants."""
        try:
            variants = await self.cross_project_synthesizer.generate_synthesis_variants(
                procedure_id,
                procedure_name,
                procedure_code,
                related_procedures,
                max_variants=config.max_variants_per_category,
            )

            return "cross_project_synthesis", variants

        except Exception as e:
            logger.error(f"Error in cross-project synthesis: {e}")
            return "cross_project_synthesis", []

    async def _generate_parameter_variants(
        self,
        procedure_id: int,
        procedure_name: str,
        procedure_code: str,
        config: DreamGenerationConfig,
    ) -> Tuple[str, List[DreamProcedure]]:
        """Generate parameter exploration variants."""
        try:
            variants = await self.parameter_explorer.generate_parameter_variants(
                procedure_id,
                procedure_name,
                procedure_code,
                max_variants=config.max_variants_per_category,
            )

            return "parameter_exploration", variants

        except Exception as e:
            logger.error(f"Error in parameter exploration: {e}")
            return "parameter_exploration", []

    async def _generate_conditional_variants(
        self,
        procedure_id: int,
        procedure_name: str,
        procedure_code: str,
        config: DreamGenerationConfig,
    ) -> Tuple[str, List[DreamProcedure]]:
        """Generate conditional execution variants."""
        try:
            variants = self.conditional_generator.generate_conditional_variants(
                procedure_id, procedure_name, procedure_code, max_variants=5
            )

            return "conditional_variants", variants

        except Exception as e:
            logger.error(f"Error in conditional variants: {e}")
            return "conditional_variants", []

    async def close(self):
        """Close OpenRouter client."""
        await self.client.close()

    async def __aenter__(self):
        """Async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Convenience function for typical usage
async def generate_dreams(
    procedure_id: int,
    procedure_name: str,
    procedure_code: str,
    strategy: str = "balanced",
    related_procedures: Optional[List[ProcedureReference]] = None,
) -> List[DreamProcedure]:
    """
    Generate dreams for a procedure.

    Typical usage:
        dreams = await generate_dreams(
            procedure_id=1,
            procedure_name="deploy_api",
            procedure_code=code,
            strategy="balanced"
        )
    """
    config = DreamGenerationConfig.from_strategy(strategy)

    async with DreamGenerator() as generator:
        return await generator.generate_dreams(
            procedure_id=procedure_id,
            procedure_name=procedure_name,
            procedure_code=procedure_code,
            related_procedures=related_procedures,
            config=config,
        )
