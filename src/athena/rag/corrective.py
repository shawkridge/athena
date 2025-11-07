"""Corrective RAG (CRAG) - Validates and corrects retrieved documents.

CRAG framework:
1. Retrieve documents from knowledge base
2. Evaluate document relevance to query
3. If relevant: use document as-is
4. If partially relevant: refine/correct document
5. If irrelevant: trigger web search for supplemental info
6. Aggregate results with confidence scoring

This implementation focuses on document validation and correction,
building on top of existing RAG infrastructure.
"""

import logging
from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict, Any

from ..core.models import MemorySearchResult
from .llm_client import LLMClient

logger = logging.getLogger(__name__)


@dataclass
class CRAGConfig:
    """Configuration for CRAG system."""

    # Relevance thresholds
    relevance_threshold_high: float = 0.8  # Definitely relevant
    relevance_threshold_low: float = 0.4  # Might need refinement
    # Below low threshold = trigger web search

    # Validation settings
    validate_factuality: bool = True  # Check for factual accuracy
    validate_completeness: bool = True  # Check if document answers query
    validate_consistency: bool = True  # Check for internal consistency

    # Correction settings
    correction_max_attempts: int = 2  # Max refinement iterations
    use_web_search_fallback: bool = True  # Fall back to web search if needed

    # Performance settings
    batch_size: int = 5  # Batch validation requests
    cache_validations: bool = True  # Cache validation results


@dataclass
class DocumentValidation:
    """Result of document validation."""

    document_id: str
    query: str
    relevance_score: float  # 0-1, higher = more relevant
    relevance_label: str  # "relevant", "partially_relevant", "irrelevant"

    # Validation details
    answers_query: bool  # Does document answer the query?
    factually_accurate: bool  # Are the facts correct?
    internally_consistent: bool  # Is the document self-consistent?

    # Corrections
    needs_correction: bool
    correction_reason: Optional[str] = None
    corrected_content: Optional[str] = None

    # Confidence
    validation_confidence: float = 1.0  # How confident in this validation

    # Metadata
    correction_applied: bool = False
    web_search_needed: bool = False


@dataclass
class CRAGResult:
    """Result from CRAG processing."""

    query: str
    original_documents: List[MemorySearchResult]
    validated_documents: List[Tuple[MemorySearchResult, DocumentValidation]]

    # Statistics
    total_documents: int
    relevant_documents: int  # Relevant + partially relevant
    corrected_documents: int
    web_search_needed: int

    # Quality metrics
    overall_relevance: float  # Weighted average relevance
    quality_score: float  # 0-1, overall quality

    # Fallback info
    web_search_results: Optional[List[str]] = None


class DocumentValidator:
    """Validates document relevance and accuracy."""

    def __init__(self, llm_client: LLMClient):
        """Initialize validator.

        Args:
            llm_client: LLM client for validation
        """
        self.llm_client = llm_client
        self._validation_cache = {}

    def validate_relevance(
        self, query: str, document_content: str, document_id: str
    ) -> DocumentValidation:
        """Validate if document is relevant to query.

        Args:
            query: User query
            document_content: Document text to validate
            document_id: Document identifier

        Returns:
            DocumentValidation with relevance assessment
        """
        # Check cache
        cache_key = (query, document_id)
        if cache_key in self._validation_cache:
            return self._validation_cache[cache_key]

        # Truncate document for validation (LLM context limits)
        truncated_content = document_content[:2000]

        # Prepare validation prompt
        validation_prompt = f"""Analyze the relevance of this document to the query.

Query: {query}

Document (ID: {document_id}):
{truncated_content}

Evaluate:
1. Does the document answer the query? (yes/no)
2. Is the content factually accurate? (yes/no/uncertain)
3. Is the document internally consistent? (yes/no)
4. Overall relevance score (0-1)
5. If not fully relevant, what's missing or incorrect?

Respond in JSON format:
{{
  "answers_query": boolean,
  "factually_accurate": boolean,
  "internally_consistent": boolean,
  "relevance_score": float,
  "reasoning": "brief explanation"
}}"""

        try:
            # Get LLM validation
            response = self.llm_client.query(validation_prompt)
            validation_data = self._parse_validation_response(response)
        except Exception as e:
            logger.warning(f"Validation failed for {document_id}: {e}, using fallback")
            # Fallback: simple keyword matching
            validation_data = self._fallback_validation(query, document_content)

        # Create validation result
        relevance_score = validation_data.get("relevance_score", 0.5)

        if relevance_score >= 0.8:
            relevance_label = "relevant"
        elif relevance_score >= 0.4:
            relevance_label = "partially_relevant"
        else:
            relevance_label = "irrelevant"

        validation = DocumentValidation(
            document_id=document_id,
            query=query,
            relevance_score=relevance_score,
            relevance_label=relevance_label,
            answers_query=validation_data.get("answers_query", False),
            factually_accurate=validation_data.get("factually_accurate", True),
            internally_consistent=validation_data.get("internally_consistent", True),
            needs_correction=(
                not validation_data.get("answers_query", False)
                or not validation_data.get("factually_accurate", True)
            ),
            correction_reason=validation_data.get("reasoning"),
            validation_confidence=min(1.0, relevance_score + 0.2),
        )

        # Cache result
        self._validation_cache[cache_key] = validation
        return validation

    def _parse_validation_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM validation response.

        Args:
            response: LLM response text

        Returns:
            Parsed validation data
        """
        import json
        import re

        # Try to extract JSON from response
        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Fallback parsing
        return {
            "answers_query": "yes" in response.lower(),
            "factually_accurate": "accurate" in response.lower(),
            "internally_consistent": "consistent" in response.lower(),
            "relevance_score": 0.5,
            "reasoning": response[:200],
        }

    def _fallback_validation(self, query: str, document_content: str) -> Dict[str, Any]:
        """Fallback validation using simple heuristics.

        Args:
            query: User query
            document_content: Document content

        Returns:
            Validation scores
        """
        query_words = set(query.lower().split())
        doc_words = set(document_content.lower().split())

        # Jaccard similarity
        intersection = len(query_words & doc_words)
        union = len(query_words | doc_words)
        similarity = intersection / union if union > 0 else 0.0

        return {
            "answers_query": similarity > 0.3,
            "factually_accurate": True,  # Can't verify without LLM
            "internally_consistent": True,  # Can't verify without LLM
            "relevance_score": similarity,
            "reasoning": f"Keyword overlap: {similarity:.2%}",
        }

    def clear_cache(self):
        """Clear validation cache."""
        self._validation_cache.clear()


class DocumentCorrector:
    """Corrects and refines documents."""

    def __init__(self, llm_client: LLMClient):
        """Initialize corrector.

        Args:
            llm_client: LLM client for corrections
        """
        self.llm_client = llm_client

    def correct_document(
        self, query: str, document_content: str, issue: str, max_attempts: int = 2
    ) -> Tuple[str, bool]:
        """Correct a document based on validation issues.

        Args:
            query: User query
            document_content: Original document content
            issue: Description of what needs to be corrected
            max_attempts: Maximum correction attempts

        Returns:
            Tuple of (corrected_content, success_flag)
        """
        correction_prompt = f"""The following document has an issue with relevance to the query.

Query: {query}

Issue: {issue}

Original Document:
{document_content[:1500]}

Please provide a corrected or refined version that:
1. Directly addresses the query
2. Maintains factual accuracy
3. Removes irrelevant sections
4. Adds context if needed

Provide the corrected document in clear, concise text."""

        try:
            corrected = self.llm_client.query(correction_prompt)
            return corrected, True
        except Exception as e:
            logger.warning(f"Correction failed: {e}")
            return document_content, False

    def refine_with_context(
        self, query: str, document_content: str, context_info: List[str]
    ) -> str:
        """Refine document by adding contextual information.

        Args:
            query: User query
            document_content: Original document
            context_info: Additional context to incorporate

        Returns:
            Refined document content
        """
        context_str = "\n".join([f"- {c}" for c in context_info[:3]])  # Top 3 context items

        refine_prompt = f"""Enhance this document with additional context while maintaining quality.

Query: {query}

Original Document:
{document_content[:1000]}

Additional Context to Incorporate:
{context_str}

Please enhance the document by:
1. Incorporating relevant context
2. Improving clarity
3. Maintaining original structure
4. Keeping all facts accurate

Provide the enhanced document."""

        try:
            return self.llm_client.query(refine_prompt)
        except Exception:
            return document_content


class CorrectiveRAGManager:
    """Main CRAG manager - orchestrates validation and correction."""

    def __init__(
        self,
        llm_client: LLMClient,
        config: Optional[CRAGConfig] = None,
    ):
        """Initialize CRAG manager.

        Args:
            llm_client: LLM client for validation and correction
            config: CRAG configuration (uses defaults if None)
        """
        self.llm_client = llm_client
        self.config = config or CRAGConfig()
        self.validator = DocumentValidator(llm_client)
        self.corrector = DocumentCorrector(llm_client)

    def process_documents(
        self, query: str, documents: List[MemorySearchResult]
    ) -> CRAGResult:
        """Process documents through CRAG pipeline.

        Args:
            query: User query
            documents: Retrieved documents to validate and correct

        Returns:
            CRAGResult with validated/corrected documents
        """
        # Validate all documents
        validations = []
        corrected_docs = []
        web_search_needed_count = 0

        for doc in documents:
            # Validate relevance
            validation = self.validator.validate_relevance(
                query, doc.content, doc.id
            )
            validations.append((doc, validation))

            # Correct if needed
            if validation.needs_correction and validation.relevance_score > self.config.relevance_threshold_low:
                corrected_content, success = self.corrector.correct_document(
                    query, doc.content, validation.correction_reason or "Missing details"
                )
                if success:
                    validation.corrected_content = corrected_content
                    validation.correction_applied = True
                    corrected_docs.append(doc)

            # Mark for web search if irrelevant
            if validation.relevance_score < self.config.relevance_threshold_low:
                validation.web_search_needed = True
                web_search_needed_count += 1

        # Calculate statistics
        relevant_count = sum(
            1 for _, v in validations
            if v.relevance_score >= self.config.relevance_threshold_low
        )

        overall_relevance = (
            sum(v.relevance_score for _, v in validations) / len(validations)
            if validations
            else 0.0
        )

        # Calculate quality score
        quality_score = self._calculate_quality_score(validations)

        return CRAGResult(
            query=query,
            original_documents=documents,
            validated_documents=validations,
            total_documents=len(documents),
            relevant_documents=relevant_count,
            corrected_documents=len(corrected_docs),
            web_search_needed=web_search_needed_count,
            overall_relevance=overall_relevance,
            quality_score=quality_score,
        )

    def _calculate_quality_score(
        self, validations: List[Tuple[Any, DocumentValidation]]
    ) -> float:
        """Calculate overall quality score.

        Args:
            validations: List of document validations

        Returns:
            Quality score 0-1
        """
        if not validations:
            return 0.0

        # Weight factors
        relevance_weight = 0.4
        accuracy_weight = 0.3
        consistency_weight = 0.2
        confidence_weight = 0.1

        relevance_avg = sum(v.relevance_score for _, v in validations) / len(validations)
        accuracy_avg = sum(1.0 if v.factually_accurate else 0.0 for _, v in validations) / len(
            validations
        )
        consistency_avg = sum(
            1.0 if v.internally_consistent else 0.0 for _, v in validations
        ) / len(validations)
        confidence_avg = sum(v.validation_confidence for _, v in validations) / len(validations)

        return (
            relevance_avg * relevance_weight
            + accuracy_avg * accuracy_weight
            + consistency_avg * consistency_weight
            + confidence_avg * confidence_weight
        )

    def get_relevant_documents(
        self, crag_result: CRAGResult
    ) -> List[Tuple[MemorySearchResult, str]]:
        """Get documents that passed relevance threshold.

        Args:
            crag_result: CRAG processing result

        Returns:
            List of (document, content) tuples for relevant documents
        """
        results = []

        for doc, validation in crag_result.validated_documents:
            if validation.relevance_score >= self.config.relevance_threshold_low:
                content = validation.corrected_content or doc.content
                results.append((doc, content))

        return results

    def get_summary(self, crag_result: CRAGResult) -> Dict[str, Any]:
        """Get summary of CRAG processing.

        Args:
            crag_result: CRAG processing result

        Returns:
            Summary dictionary
        """
        return {
            "query": crag_result.query,
            "total_documents": crag_result.total_documents,
            "relevant_documents": crag_result.relevant_documents,
            "corrected_documents": crag_result.corrected_documents,
            "web_search_needed": crag_result.web_search_needed,
            "overall_relevance": round(crag_result.overall_relevance, 3),
            "quality_score": round(crag_result.quality_score, 3),
            "success_rate": round(crag_result.relevant_documents / crag_result.total_documents, 2)
            if crag_result.total_documents > 0
            else 0.0,
        }

    def clear_cache(self):
        """Clear all internal caches."""
        self.validator.clear_cache()
