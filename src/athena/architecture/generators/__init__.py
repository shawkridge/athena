"""Document generation module.

Provides AI-powered and template-based document generation from specifications.
"""

from .context_assembler import ContextAssembler, GenerationContext
from .ai_generator import AIDocGenerator
from .prompts import PromptLibrary

__all__ = [
    "ContextAssembler",
    "GenerationContext",
    "AIDocGenerator",
    "PromptLibrary",
]
