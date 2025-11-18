"""Parser for Claude's dream evaluation responses."""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class DreamEvaluation:
    """Parsed evaluation for a single dream."""

    dream_id_or_name: str
    viability_score: float
    tier: int
    reasoning: str


class DreamEvaluationParser:
    """
    Parse Claude's natural language dream evaluations into structured data.

    Supports multiple response formats:
    - Structured lists with numbered dreams
    - JSON-like format
    - Natural prose with clear markers
    """

    def __init__(self):
        """Initialize the parser."""
        self.score_patterns = [
            # "viability: 0.8", "score: 0.8", "confidence: 0.8"
            r"(?:viability|score|confidence)[\s:]+([0-9]\.[0-9]|1\.0|0\.0)",
            # "0.8/1.0", "0.8 out of 1.0"
            r"([0-9]\.[0-9])\s*(?:/|out\s+of)\s*1\.?0?",
            # "80%", "80 percent"
            r"([0-9]+)\s*(?:%|percent)",
        ]

        self.tier_patterns = [
            # "tier 1", "tier1", "tier: 1"
            r"tier[\s:]*([1-3])",
            # "Tier 1: Viable", etc.
            r"(?:viable|speculative|archive)(?:\s+\()?tier\s+([1-3])",
        ]

    def parse_evaluations(self, response_text: str) -> List[DreamEvaluation]:
        """
        Parse Claude's response to extract dream evaluations.

        Args:
            response_text: Claude's natural language response

        Returns:
            List of DreamEvaluation objects
        """
        evaluations = []

        # Try multiple parsing strategies
        evals = self._parse_structured_list(response_text)
        if evals:
            return evals

        evals = self._parse_prose_format(response_text)
        if evals:
            return evals

        evals = self._parse_json_format(response_text)
        if evals:
            return evals

        logger.warning("Could not parse dream evaluations from response")
        return []

    def _parse_structured_list(self, text: str) -> List[DreamEvaluation]:
        """
        Parse structured list format:

        Dream 1: viability 0.8, tier 1
        Dream 2: viability 0.4, tier 2
        """
        evaluations = []

        # Split by dream markers
        dream_blocks = re.split(
            r"(?:^|\n)(?:Dream|Variant|Procedure)\s+([0-9]+|[A-Za-z_]+):?", text, flags=re.MULTILINE
        )

        # Process pairs of (dream_id, content)
        for i in range(1, len(dream_blocks), 2):
            if i + 1 < len(dream_blocks):
                dream_id = dream_blocks[i].strip()
                content = dream_blocks[i + 1]

                eval = self._extract_evaluation_from_content(dream_id, content)
                if eval:
                    evaluations.append(eval)

        return evaluations

    def _parse_prose_format(self, text: str) -> List[DreamEvaluation]:
        """
        Parse prose format with natural language descriptions.

        Example:
        "Procedure A looks promising with a viability score of 0.8.
         This is a tier 1 dream because it respects all dependencies."
        """
        evaluations = []

        # Try to find dream references (Dream 1, Dream A, Procedure name, etc.)
        dream_refs = re.finditer(
            r"(?:Dream|Variant|Procedure|Alternative)\s+([0-9A-Za-z_\s]+?)(?=[.,:;])",
            text,
            re.IGNORECASE,
        )

        for match in dream_refs:
            dream_id = match.group(1).strip()

            # Extract evaluation from context around this match
            start = max(0, match.start() - 100)
            end = min(len(text), match.end() + 300)
            context = text[start:end]

            eval = self._extract_evaluation_from_content(dream_id, context)
            if eval:
                evaluations.append(eval)

        return evaluations

    def _parse_json_format(self, text: str) -> List[DreamEvaluation]:
        """
        Parse JSON-like format.

        Example:
        [{
          "dream": "Dream 1",
          "viability": 0.8,
          "tier": 1,
          "reasoning": "..."
        }]
        """
        import json

        # Find JSON blocks in the response
        json_pattern = r"\[[\s\S]*?\]|\{[\s\S]*?\}"
        json_blocks = re.findall(json_pattern, text)

        evaluations = []

        for block in json_blocks:
            try:
                data = json.loads(block)

                # Handle list of objects
                if isinstance(data, list):
                    for item in data:
                        eval = self._extract_from_json_object(item)
                        if eval:
                            evaluations.append(eval)

                # Handle single object
                elif isinstance(data, dict):
                    eval = self._extract_from_json_object(data)
                    if eval:
                        evaluations.append(eval)

            except json.JSONDecodeError:
                continue

        return evaluations

    def _extract_evaluation_from_content(
        self, dream_id: str, content: str
    ) -> Optional[DreamEvaluation]:
        """Extract evaluation metrics from content text."""
        score = self._extract_score(content)
        tier = self._extract_tier(content)
        reasoning = self._extract_reasoning(content, limit=200)

        if score is None or tier is None:
            return None

        return DreamEvaluation(
            dream_id_or_name=dream_id, viability_score=score, tier=tier, reasoning=reasoning
        )

    def _extract_from_json_object(self, obj: Dict) -> Optional[DreamEvaluation]:
        """Extract evaluation from JSON object."""
        # Find dream identifier
        dream_id = None
        for key in ("dream", "name", "id", "dream_name"):
            if key in obj:
                dream_id = str(obj[key])
                break

        if not dream_id:
            return None

        # Extract score
        score = None
        for key in ("viability", "score", "viability_score", "confidence"):
            if key in obj:
                try:
                    score = float(obj[key])
                    if score > 1.0:
                        score = score / 100.0  # Convert percentage
                    break
                except (ValueError, TypeError):
                    pass

        # Extract tier
        tier = None
        for key in ("tier", "tier_number", "category"):
            if key in obj:
                try:
                    tier = int(obj[key])
                    break
                except (ValueError, TypeError):
                    pass

        if score is None or tier is None:
            return None

        # Extract reasoning
        reasoning = obj.get("reasoning", obj.get("reason", ""))

        return DreamEvaluation(
            dream_id_or_name=dream_id, viability_score=score, tier=tier, reasoning=str(reasoning)
        )

    def _extract_score(self, text: str) -> Optional[float]:
        """Extract viability score from text."""
        for pattern in self.score_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    score = float(match.group(1))
                    # Normalize percentage to 0-1 range
                    if score > 1.0:
                        score = score / 100.0
                    # Clamp to [0, 1]
                    return max(0.0, min(1.0, score))
                except (ValueError, IndexError):
                    continue

        return None

    def _extract_tier(self, text: str) -> Optional[int]:
        """Extract tier number from text."""
        for pattern in self.tier_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    tier = int(match.group(1))
                    if 1 <= tier <= 3:
                        return tier
                except (ValueError, IndexError):
                    continue

        return None

    def _extract_reasoning(self, text: str, limit: int = 200) -> str:
        """Extract reasoning text."""
        # Look for explicit reasoning sections
        reasoning_patterns = [
            r"reason(?:ing)?:\s*([^.\n]+)",
            r"because\s+([^.\n]+)",
            r"explanation:\s*([^\n]+)",
        ]

        for pattern in reasoning_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                reason = match.group(1).strip()
                return reason[:limit]

        # Fall back to first sentence
        sentences = re.split(r"[.!?]", text)
        if sentences:
            return sentences[0][:limit].strip()

        return ""

    def validate_evaluation(self, eval: DreamEvaluation) -> Tuple[bool, str]:
        """
        Validate an evaluation for correctness.

        Returns:
            (is_valid, error_message)
        """
        if not eval.dream_id_or_name:
            return False, "Missing dream identifier"

        if not (0.0 <= eval.viability_score <= 1.0):
            return False, f"Viability score {eval.viability_score} out of range [0, 1]"

        if eval.tier not in (1, 2, 3):
            return False, f"Tier {eval.tier} not in [1, 2, 3]"

        if not eval.reasoning:
            return False, "Missing reasoning"

        return True, ""


# Convenience function
def parse_dream_evaluations(response_text: str) -> List[DreamEvaluation]:
    """
    Parse dream evaluations from Claude's response.

    Usage:
        evaluations = parse_dream_evaluations(claude_response)
        for eval in evaluations:
            print(f"Dream {eval.dream_id_or_name}: {eval.viability_score}")
    """
    parser = DreamEvaluationParser()
    return parser.parse_evaluations(response_text)
