"""AI-powered document generation.

Uses Claude to generate high-quality documentation from specifications
and architectural artifacts.
"""

import logging
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from ..models import Document, DocumentType, DocumentStatus
from .context_assembler import GenerationContext
from .prompts import PromptLibrary

logger = logging.getLogger(__name__)


@dataclass
class GenerationResult:
    """Result of AI document generation."""

    content: str
    doc_type: DocumentType

    # Generation metadata
    model: str
    prompt: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    # Quality metrics
    confidence: float = 0.0
    warnings: List[str] = None

    # Context used
    context_summary: str = ""

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []

    def to_document(
        self,
        project_id: int,
        name: str,
        version: str = "1.0.0",
        file_path: Optional[str] = None,
        **kwargs
    ) -> Document:
        """Convert generation result to Document model.

        Args:
            project_id: Project ID
            name: Document name
            version: Version string
            file_path: Optional file path
            **kwargs: Additional document fields

        Returns:
            Document instance ready for storage
        """
        # Compute sync hash from content
        sync_hash = hashlib.sha256(self.content.encode()).hexdigest()[:16]

        return Document(
            project_id=project_id,
            name=name,
            doc_type=self.doc_type,
            version=version,
            status=DocumentStatus.DRAFT,
            content=self.content,
            file_path=file_path,
            generated_by="ai",
            generation_model=self.model,
            generation_prompt=self.prompt,
            sync_hash=sync_hash,
            last_synced_at=datetime.now(),
            **kwargs
        )


class AIDocGenerator:
    """AI-powered document generator using Claude.

    Generates high-quality documentation from specifications using
    specialized prompts and intelligent context assembly.

    Example:
        >>> generator = AIDocGenerator(api_key="sk-...")
        >>> context = ContextAssembler(...).assemble_for_spec(5)
        >>> result = generator.generate(
        ...     doc_type=DocumentType.API_DOC,
        ...     context=context
        ... )
        >>> print(f"Generated {len(result.content)} characters")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022",
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ):
        """Initialize AI document generator.

        Args:
            api_key: Anthropic API key (uses env var if not provided)
            model: Claude model to use
            max_tokens: Maximum tokens for completion
            temperature: Generation temperature (0-1)

        Raises:
            ImportError: If anthropic package not installed
        """
        if not ANTHROPIC_AVAILABLE:
            raise ImportError(
                "anthropic package is required for AI generation. "
                "Install with: pip install anthropic"
            )

        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

        logger.info(f"AI generator initialized with model: {model}")

    def generate(
        self,
        doc_type: DocumentType,
        context: GenerationContext,
        custom_instructions: Optional[str] = None,
    ) -> GenerationResult:
        """Generate documentation using AI.

        Args:
            doc_type: Type of document to generate
            context: Generation context with specs and artifacts
            custom_instructions: Optional custom instructions to append

        Returns:
            Generation result with content and metadata

        Example:
            >>> result = generator.generate(
            ...     doc_type=DocumentType.TDD,
            ...     context=context,
            ...     custom_instructions="Focus on security considerations"
            ... )
        """
        # Get prompt for document type
        context_dict = context.to_dict()
        context_dict["doc_type"] = doc_type.value

        base_prompt = PromptLibrary.get_prompt(doc_type, context_dict)

        # Add custom instructions if provided
        prompt = base_prompt
        if custom_instructions:
            prompt += f"\n\n# Additional Instructions\n\n{custom_instructions}\n"

        logger.info(f"Generating {doc_type.value} document using {self.model}")
        logger.debug(f"Context: {context.get_summary()}")

        # Call Claude API
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Extract generated content
            content = response.content[0].text

            # Get token usage
            usage = response.usage
            prompt_tokens = usage.input_tokens
            completion_tokens = usage.output_tokens
            total_tokens = prompt_tokens + completion_tokens

            logger.info(
                f"Generation complete: {len(content)} chars, "
                f"{total_tokens} tokens ({prompt_tokens} prompt + {completion_tokens} completion)"
            )

            # Compute confidence based on content quality
            confidence = self._compute_confidence(content, doc_type)

            # Check for potential issues
            warnings = self._check_quality(content, doc_type)

            return GenerationResult(
                content=content,
                doc_type=doc_type,
                model=self.model,
                prompt=prompt,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                confidence=confidence,
                warnings=warnings,
                context_summary=context.get_summary(),
            )

        except Exception as e:
            logger.error(f"AI generation failed: {e}")
            raise

    def generate_from_spec(
        self,
        spec_id: int,
        doc_type: DocumentType,
        spec_store,
        **kwargs
    ) -> GenerationResult:
        """Generate documentation directly from a specification ID.

        Convenience method that assembles context and generates in one call.

        Args:
            spec_id: Specification ID
            doc_type: Type of document to generate
            spec_store: Specification store instance
            **kwargs: Additional arguments for context assembly

        Returns:
            Generation result

        Example:
            >>> result = generator.generate_from_spec(
            ...     spec_id=5,
            ...     doc_type=DocumentType.API_DOC,
            ...     spec_store=store
            ... )
        """
        from .context_assembler import ContextAssembler

        # Assemble context
        assembler = ContextAssembler(spec_store=spec_store)
        context = assembler.assemble_for_spec(
            spec_id=spec_id,
            doc_type=doc_type,
            **kwargs
        )

        # Generate documentation
        return self.generate(
            doc_type=doc_type,
            context=context,
            custom_instructions=kwargs.get("custom_instructions")
        )

    def _compute_confidence(self, content: str, doc_type: DocumentType) -> float:
        """Compute confidence score for generated content.

        Args:
            content: Generated content
            doc_type: Document type

        Returns:
            Confidence score (0-1)
        """
        confidence = 0.8  # Base confidence

        # Check content length
        if len(content) < 500:
            confidence -= 0.2  # Too short
        elif len(content) > 10000:
            confidence -= 0.1  # Very long, may be verbose

        # Check for key sections based on doc type
        if doc_type in [DocumentType.API_DOC, DocumentType.API_GUIDE]:
            if "authentication" not in content.lower():
                confidence -= 0.1
            if "example" not in content.lower():
                confidence -= 0.1

        elif doc_type in [DocumentType.TDD, DocumentType.HLD]:
            if "architecture" not in content.lower():
                confidence -= 0.1
            if "design" not in content.lower():
                confidence -= 0.1

        # Check for markdown formatting
        if content.count("#") < 3:
            confidence -= 0.1  # Insufficient headers

        return max(0.0, min(1.0, confidence))

    def _check_quality(self, content: str, doc_type: DocumentType) -> List[str]:
        """Check for quality issues in generated content.

        Args:
            content: Generated content
            doc_type: Document type

        Returns:
            List of warning messages
        """
        warnings = []

        # Check length
        if len(content) < 500:
            warnings.append("Content is very short - may be incomplete")

        # Check for placeholder text
        if "TODO" in content or "FIXME" in content or "[placeholder]" in content.lower():
            warnings.append("Content contains placeholders that need filling")

        # Check for markdown formatting
        if content.count("#") < 3:
            warnings.append("Content has few section headers - may lack structure")

        # Check for code examples (for technical docs)
        if doc_type in [
            DocumentType.API_DOC,
            DocumentType.API_GUIDE,
            DocumentType.SDK_DOC,
            DocumentType.TDD,
        ]:
            if "```" not in content:
                warnings.append("No code examples found - consider adding examples")

        # Check for diagrams (for architecture docs)
        if doc_type in [
            DocumentType.HLD,
            DocumentType.TDD,
            DocumentType.ARC42,
            DocumentType.C4_CONTEXT,
            DocumentType.C4_CONTAINER,
        ]:
            if "mermaid" not in content.lower() and "diagram" not in content.lower():
                warnings.append("No diagrams found - consider adding architecture diagrams")

        return warnings
