"""System 2 LLM-based pattern validation for semantic correctness."""

import json
import logging
from typing import Optional, List, Dict, Any

from ..core.config import (
    LLM_PROVIDER,
    CLAUDE_API_KEY,
    CLAUDE_MODEL,
    LLAMACPP_REASONING_URL,
    ENABLE_LLM_FEATURES,
)
from .task_patterns import TaskPattern, PatternStatus, ExtractionMethod

logger = logging.getLogger(__name__)


class PatternValidator:
    """Validates patterns using LLM (System 2: semantic validation).

    System 2 is triggered when:
    - Pattern confidence < 0.8 (statistical uncertainty)
    - Pattern contradicts existing patterns
    - User explicitly requests validation

    Validation checks:
    1. Semantic sensibility: Does the pattern make logical sense?
    2. Generalization: Is it too specific or too general?
    3. Contradiction detection: Conflicts with other patterns?
    4. Edge cases: Are there obvious exceptions?
    """

    CONFIDENCE_THRESHOLD = 0.8  # Trigger System 2 if below this

    def __init__(self, provider: str = LLM_PROVIDER):
        """Initialize pattern validator.

        Args:
            provider: LLM provider to use (ollama, llamacpp, claude)
        """
        self.provider = provider
        self.enable_llm = ENABLE_LLM_FEATURES

        if not self.enable_llm:
            logger.warning("LLM features disabled - pattern validation will be limited")

    def validate_pattern(
        self,
        pattern: TaskPattern,
        existing_patterns: List[TaskPattern] = None,
    ) -> Dict[str, Any]:
        """Validate a single pattern using System 2.

        Args:
            pattern: TaskPattern to validate
            existing_patterns: Other patterns to check for contradictions

        Returns:
            Dict with validation results:
            {
                'is_valid': bool,
                'confidence_adjustment': float,  # Amount to adjust confidence by
                'validation_notes': str,
                'contradictions': [pattern_ids],
                'recommendations': [str],
            }
        """
        if not self.enable_llm:
            return self._fallback_validation(pattern, existing_patterns)

        try:
            # Check if validation is even needed
            if pattern.confidence_score >= self.CONFIDENCE_THRESHOLD:
                logger.debug(
                    f"Pattern {pattern.pattern_name} already high confidence "
                    f"({pattern.confidence_score:.2f}), skipping validation"
                )
                return {
                    "is_valid": True,
                    "confidence_adjustment": 0.0,
                    "validation_notes": "Already high confidence from statistical analysis",
                    "contradictions": [],
                    "recommendations": [],
                }

            # Perform LLM validation
            if self.provider == "claude":
                return self._validate_with_claude(pattern, existing_patterns)
            elif self.provider in ["llamacpp", "ollama"]:
                return self._validate_with_local_llm(pattern, existing_patterns)
            else:
                logger.warning(f"Unknown LLM provider: {self.provider}")
                return self._fallback_validation(pattern, existing_patterns)

        except Exception as e:
            logger.error(f"Error validating pattern: {e}", exc_info=True)
            return self._fallback_validation(pattern, existing_patterns)

    def validate_patterns_batch(
        self,
        patterns: List[TaskPattern],
        existing_patterns: List[TaskPattern] = None,
    ) -> Dict[int, Dict[str, Any]]:
        """Validate multiple patterns efficiently.

        Args:
            patterns: List of patterns to validate
            existing_patterns: Existing patterns for contradiction checking

        Returns:
            Dict mapping pattern_id to validation results
        """
        results = {}

        # Filter patterns that need validation
        to_validate = [
            p for p in patterns
            if p.confidence_score < self.CONFIDENCE_THRESHOLD
        ]

        if not to_validate:
            logger.info("All patterns already high confidence, skipping validation")
            return results

        logger.info(f"Validating {len(to_validate)} patterns that need semantic review")

        for pattern in to_validate:
            result = self.validate_pattern(pattern, existing_patterns)
            results[pattern.id or 0] = result

        return results

    def _validate_with_claude(
        self,
        pattern: TaskPattern,
        existing_patterns: List[TaskPattern] = None,
    ) -> Dict[str, Any]:
        """Validate pattern using Claude API."""
        try:
            import anthropic

            # Build validation prompt
            prompt = self._build_validation_prompt(pattern, existing_patterns)

            client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
            message = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=500,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )

            # Parse response
            response_text = message.content[0].text
            return self._parse_validation_response(response_text, pattern)

        except ImportError:
            logger.warning("anthropic library not available, falling back")
            return self._fallback_validation(pattern, existing_patterns)
        except Exception as e:
            logger.error(f"Error validating with Claude: {e}")
            return self._fallback_validation(pattern, existing_patterns)

    def _validate_with_local_llm(
        self,
        pattern: TaskPattern,
        existing_patterns: List[TaskPattern] = None,
    ) -> Dict[str, Any]:
        """Validate pattern using local llama.cpp server."""
        try:
            import requests

            # Build validation prompt
            prompt = self._build_validation_prompt(pattern, existing_patterns)

            # Call local LLM server
            response = requests.post(
                LLAMACPP_REASONING_URL + "/completion",
                json={
                    "prompt": prompt,
                    "temperature": 0.3,  # Low temperature for consistency
                    "n_predict": 500,
                    "stop": ["</response>"],
                },
                timeout=30,
            )

            if response.status_code != 200:
                logger.warning(f"Local LLM returned {response.status_code}")
                return self._fallback_validation(pattern, existing_patterns)

            result = response.json()
            response_text = result.get("content", "")

            return self._parse_validation_response(response_text, pattern)

        except Exception as e:
            logger.error(f"Error validating with local LLM: {e}")
            return self._fallback_validation(pattern, existing_patterns)

    def _build_validation_prompt(
        self,
        pattern: TaskPattern,
        existing_patterns: List[TaskPattern] = None,
    ) -> str:
        """Build validation prompt for LLM."""
        prompt = f"""You are a task pattern validator. Analyze this task execution pattern for semantic correctness.

PATTERN TO VALIDATE:
- Name: {pattern.pattern_name}
- Type: {pattern.pattern_type}
- Description: {pattern.description}
- Conditions: {pattern.condition_json}
- Prediction: {pattern.prediction}
- Success Rate: {pattern.success_rate:.1%}
- Sample Size: {pattern.sample_size}
- Statistical Confidence: {pattern.confidence_score:.2f}

EVALUATION CRITERIA:
1. SEMANTIC SENSE: Does this pattern make logical sense? (yes/no + reason)
2. GENERALIZATION: Is it too specific (overfitting) or appropriately general? (appropriate/too_specific/too_general)
3. CONTRADICTION: Are there obvious counter-examples or contradictions? (yes/no + examples)
4. ACTIONABILITY: Can this pattern be used to improve planning? (yes/no)

EXISTING PATTERNS:
"""
        if existing_patterns:
            for p in existing_patterns[:5]:  # Show top 5 for context
                prompt += f"- {p.pattern_name}: {p.description}\n"
        else:
            prompt += "- (None yet)\n"

        prompt += """
RESPONSE FORMAT:
Provide a JSON response with:
{
    "is_valid": true/false,
    "semantic_score": 0.0-1.0,
    "reasoning": "Brief explanation",
    "contradicts": [],
    "recommendations": ["suggestion1", "suggestion2"]
}

Validate now:
"""
        return prompt

    def _parse_validation_response(
        self,
        response_text: str,
        pattern: TaskPattern,
    ) -> Dict[str, Any]:
        """Parse LLM validation response."""
        try:
            # Try to extract JSON from response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                data = json.loads(json_str)
            else:
                logger.warning("Could not find JSON in LLM response")
                return self._fallback_validation(None, None)

            # Extract validation scores
            is_valid = data.get("is_valid", True)
            semantic_score = data.get("semantic_score", 0.5)
            reasoning = data.get("reasoning", "")
            contradicts = data.get("contradicts", [])
            recommendations = data.get("recommendations", [])

            # Calculate confidence adjustment
            confidence_adjustment = 0.0
            if is_valid:
                # Boost confidence if LLM validates
                confidence_adjustment = min(semantic_score * 0.2, 0.15)
                validation_notes = f"LLM validated: {reasoning}"
            else:
                # Reduce confidence if issues found
                confidence_adjustment = -0.15
                validation_notes = f"LLM concerns: {reasoning}"

            return {
                "is_valid": is_valid,
                "confidence_adjustment": confidence_adjustment,
                "validation_notes": validation_notes,
                "contradictions": contradicts,
                "recommendations": recommendations,
            }

        except json.JSONDecodeError:
            logger.warning("Could not parse LLM response as JSON")
            return self._fallback_validation(None, None)

    def _fallback_validation(
        self,
        pattern: Optional[TaskPattern],
        existing_patterns: Optional[List[TaskPattern]],
    ) -> Dict[str, Any]:
        """Fallback validation when LLM is unavailable.

        Performs basic heuristic checks:
        - Sample size adequacy
        - Success rate plausibility
        - Pattern type consistency
        """
        if not pattern:
            return {
                "is_valid": False,
                "confidence_adjustment": -0.1,
                "validation_notes": "Could not validate (LLM unavailable and fallback failed)",
                "contradictions": [],
                "recommendations": [],
            }

        notes = []
        adjustments = 0.0

        # Check sample size
        if pattern.sample_size >= 30:
            notes.append("Good sample size")
            adjustments += 0.05
        elif pattern.sample_size < 10:
            notes.append("Small sample size (n<10) - may not generalize")
            adjustments -= 0.1

        # Check success rate plausibility
        if 0.3 < pattern.success_rate < 0.95:
            notes.append("Success rate is reasonable")
        else:
            notes.append("Extreme success rate - may indicate overfitting or selection bias")
            adjustments -= 0.05

        # Check failure rate alignment
        if pattern.failure_count > pattern.sample_size * 0.1:
            notes.append("Significant failure count - pattern not absolute")
        else:
            notes.append("Very few failures - pattern is strong")
            adjustments += 0.05

        return {
            "is_valid": True,  # Default to valid unless clear issues
            "confidence_adjustment": min(max(adjustments, -0.15), 0.15),
            "validation_notes": "; ".join(notes),
            "contradictions": [],
            "recommendations": [
                "Monitor pattern accuracy in production",
                "Compare with similar patterns",
            ],
        }

    def apply_validation_results(
        self,
        pattern: TaskPattern,
        validation_result: Dict[str, Any],
    ) -> TaskPattern:
        """Apply validation results to pattern object.

        Args:
            pattern: Original pattern
            validation_result: Validation results from validate_pattern()

        Returns:
            Updated pattern with validation applied
        """
        # Update confidence score
        new_confidence = pattern.confidence_score + validation_result.get(
            "confidence_adjustment", 0.0
        )
        pattern.confidence_score = min(max(new_confidence, 0.0), 1.0)

        # Mark as validated
        pattern.system_2_validated = True
        pattern.extraction_method = ExtractionMethod.LLM_VALIDATED

        # Set validation notes
        pattern.validation_notes = validation_result.get(
            "validation_notes", "System 2 validation applied"
        )

        # Adjust status if validation found issues
        if not validation_result.get("is_valid", True):
            if pattern.confidence_score < 0.5:
                pattern.status = PatternStatus.DEPRECATED
            else:
                pattern.status = PatternStatus.ACTIVE

        return pattern
