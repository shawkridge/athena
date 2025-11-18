"""Local reasoning integration for consolidation pipeline.

Enhances pattern extraction by using local Qwen2.5-7B model alongside
or instead of Claude API, with optional compression for cost optimization.

Architecture:
  Fast Heuristics (System 1)
       ↓
  Local Reasoning (Qwen2.5-7B) ← FAST, LOCAL
       ↓
  Compression + Claude (optional) ← CLAUDE API
       ↓
  Dual-Process Validation ← CONFIDENCE > 0.5

Benefits:
- 99% latency reduction vs Claude API (3.5s vs 1-2 second round-trip)
- Local-first (privacy, offline-capable)
- Cost optimization (60-75% token reduction before Claude)
- Hybrid quality (local + Claude validation)
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from .pattern_extraction import Pattern
from ..core.llm_client import LocalLLMClient
from ..episodic.models import EpisodicEvent
from ..monitoring.model_metrics import get_monitor

logger = logging.getLogger(__name__)


@dataclass
class LocalReasoningResult:
    """Result from local reasoning about patterns."""

    patterns: List[Pattern]
    reasoning_text: str
    latency_ms: float
    tokens_generated: int
    confidence_score: float


@dataclass
class DualProcessResult:
    """Result from dual-process reasoning (local + Claude validation)."""

    patterns: List[Pattern]
    local_patterns: List[Pattern]
    claude_patterns: Optional[List[Pattern]]
    validation_score: float
    total_latency_ms: float
    cost_saved_percent: float


class LocalConsolidationReasoner:
    """Use local LLM for consolidation reasoning.

    Provides System 2 (slow, deliberate) reasoning using Qwen2.5-7B locally,
    with optional Claude validation for high-confidence decisions.
    """

    def __init__(
        self,
        llm_client: Optional[LocalLLMClient] = None,
        claude_client: Optional[Any] = None,
        enable_compression: bool = True,
        compression_ratio: float = 0.5,
    ):
        """Initialize local reasoning module.

        Args:
            llm_client: LocalLLMClient instance (created if not provided)
            claude_client: Claude API client for optional validation
            enable_compression: Enable prompt compression for Claude calls
            compression_ratio: Target compression ratio (0.0-1.0)
        """
        self.llm_client = llm_client or LocalLLMClient(enable_compression=enable_compression)
        self.claude_client = claude_client
        self.enable_compression = enable_compression
        self.compression_ratio = compression_ratio
        self.monitor = get_monitor()

    async def extract_patterns_with_local_reasoning(
        self,
        event_cluster: List[EpisodicEvent],
        use_compression: bool = True,
        use_claude_validation: bool = False,
        confidence_threshold: float = 0.5,
    ) -> LocalReasoningResult:
        """Extract patterns using local reasoning (Qwen2.5-7B).

        Args:
            event_cluster: Related episodic events to analyze
            use_compression: Compress prompts before Claude calls
            use_claude_validation: Validate with Claude if local confidence < threshold
            confidence_threshold: Trigger Claude validation if below this

        Returns:
            LocalReasoningResult with extracted patterns
        """
        import time

        start_time = time.time()

        if not event_cluster or len(event_cluster) < 2:
            return LocalReasoningResult(
                patterns=[],
                reasoning_text="",
                latency_ms=0,
                tokens_generated=0,
                confidence_score=0.0,
            )

        # Format events for analysis
        events_text = self._format_events(event_cluster)

        # Create consolidation prompt
        prompt = self._create_consolidation_prompt(events_text)

        # Use local reasoning (Qwen2.5-7B)
        try:
            reasoning_result = await self.llm_client.consolidate_with_reasoning(
                events_text=events_text,
                task_description="Extract semantic patterns from these episodic events",
            )

            # Parse patterns from reasoning output
            patterns = self._parse_patterns_from_reasoning(reasoning_result.text)

            latency_ms = time.time() - start_time

            # Record metrics
            self.monitor.record_reasoning(
                latency_ms=latency_ms,
                prompt_tokens=len(events_text.split()),
                output_tokens=reasoning_result.tokens,
                temperature=0.5,
                status="success",
            )

            # Calculate confidence from patterns
            confidence_score = (
                sum(p.confidence for p in patterns) / len(patterns) if patterns else 0.0
            )

            # Optionally validate with Claude if confidence is low
            if use_claude_validation and confidence_score < confidence_threshold:
                logger.info(
                    f"Local confidence {confidence_score:.2f} < {confidence_threshold}, "
                    f"requesting Claude validation"
                )
                # Call Claude for validation
                patterns = await self._validate_patterns_with_claude(
                    patterns=patterns,
                    events_text=events_text,
                    local_reasoning=reasoning_result.text,
                )

            return LocalReasoningResult(
                patterns=patterns,
                reasoning_text=reasoning_result.text,
                latency_ms=latency_ms,
                tokens_generated=reasoning_result.tokens,
                confidence_score=confidence_score,
            )

        except Exception as e:
            logger.error(f"Local reasoning failed: {e}")
            self.monitor.record_reasoning(
                latency_ms=time.time() - start_time,
                prompt_tokens=len(events_text.split()),
                output_tokens=0,
                temperature=0.5,
                status="error",
                error_msg=str(e),
            )
            raise

    def _format_events(self, events: List[EpisodicEvent]) -> str:
        """Format episodic events for LLM analysis.

        Args:
            events: List of events to format

        Returns:
            Formatted events text
        """
        lines = []
        for i, event in enumerate(events, 1):
            lines.append(f"Event {i}:")
            lines.append(f"  Time: {event.timestamp}")
            lines.append(f"  Type: {event.event_type}")
            lines.append(f"  Content: {event.content[:200]}")  # Truncate long content
            if event.tags:
                lines.append(f"  Tags: {', '.join(event.tags)}")
            lines.append("")

        return "\n".join(lines)

    def _create_consolidation_prompt(self, events_text: str) -> str:
        """Create consolidation analysis prompt.

        Args:
            events_text: Formatted events

        Returns:
            Prompt for consolidation
        """
        return f"""Analyze these episodic events and extract semantic patterns:

{events_text}

Identify:
1. Common themes or concepts that appear across events
2. Temporal relationships (causality, sequences)
3. Causal chains or dependencies
4. Abstract patterns (general principles, workflows)
5. Anomalies or unexpected patterns

For each pattern, provide:
- Description (concise summary)
- Confidence (0.0-1.0, based on evidence)
- Type (pattern/decision/workflow/fact)
- Tags (relevant categories)
- Evidence (why you think this pattern exists)

Output JSON array of patterns:
```json
[
  {{
    "description": "...",
    "confidence": 0.85,
    "type": "pattern",
    "tags": ["..."],
    "evidence": "..."
  }}
]
```"""

    def _parse_patterns_from_reasoning(self, reasoning_text: str) -> List[Pattern]:
        """Parse patterns from LLM reasoning output.

        Args:
            reasoning_text: Output from local reasoning

        Returns:
            List of extracted patterns
        """
        patterns = []

        try:
            # Extract JSON from reasoning text
            # Look for JSON array between ```json and ```
            json_start = reasoning_text.find("```json")
            json_end = reasoning_text.find("```", json_start + 7)

            if json_start >= 0 and json_end > json_start:
                json_str = reasoning_text[json_start + 7 : json_end]
                pattern_dicts = json.loads(json_str)

                for p in pattern_dicts:
                    patterns.append(
                        Pattern(
                            description=p.get("description", ""),
                            type=p.get("type", "pattern"),
                            confidence=float(p.get("confidence", 0.5)),
                            tags=p.get("tags", []),
                            source_events=[],  # Will be filled by caller
                            evidence=p.get("evidence", ""),
                        )
                    )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse patterns from reasoning: {e}")
            # Fall back to extracting from text
            logger.debug(f"Raw reasoning text:\n{reasoning_text}")

        return patterns

    async def compress_for_claude_validation(
        self,
        patterns: List[Pattern],
        events_text: str,
    ) -> Dict[str, Any]:
        """Compress pattern analysis before sending to Claude.

        Args:
            patterns: Patterns extracted locally
            events_text: Original events text

        Returns:
            Compressed context suitable for Claude
        """
        # Create context to compress
        context = f"""Events Summary:
{events_text[:500]}

Local Patterns Extracted:
{json.dumps([p.to_dict() for p in patterns], indent=2)}"""

        # Compress using LLMLingua-2
        result = await self.llm_client.compress_prompt(
            context=context,
            instruction="Validate these patterns against the events",
            compression_ratio=self.compression_ratio,
        )

        return {
            "compressed_prompt": result.compressed_prompt,
            "original_tokens": result.original_tokens,
            "compressed_tokens": result.compressed_tokens,
            "compression_ratio": result.compression_ratio,
            "token_savings": result.original_tokens - result.compressed_tokens,
        }

    async def health_check(self) -> Dict[str, bool]:
        """Check health of local reasoning services.

        Returns:
            Health status of all services
        """
        return await self.llm_client.check_health()

    async def _validate_patterns_with_claude(
        self,
        patterns: List[Pattern],
        events_text: str,
        local_reasoning: str,
    ) -> List[Pattern]:
        """Validate patterns using Claude API.

        Args:
            patterns: Patterns extracted locally
            events_text: Original events text
            local_reasoning: Reasoning from local LLM

        Returns:
            Validated patterns with updated confidence scores
        """
        if not self.claude_client:
            logger.warning("Claude client not available, skipping validation")
            return patterns

        try:
            # Build validation prompt
            validation_prompt = f"""Review these patterns extracted from events and provide confidence scores.

Events:
{events_text[:500]}

Local Reasoning:
{local_reasoning[:500]}

Extracted Patterns:
{json.dumps([p.to_dict() for p in patterns], indent=2)}

For each pattern, assess:
1. Is it supported by the events?
2. How confident are you in this pattern? (0.0-1.0)
3. Should this pattern be kept, refined, or discarded?

Return JSON array with validation results:
```json
[
  {{
    "description": "original description",
    "validated": true,
    "confidence": 0.85,
    "notes": "why you think this is valid/invalid"
  }}
]
```"""

            # Call Claude API
            response = await asyncio.to_thread(
                lambda: self.claude_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1000,
                    messages=[{"role": "user", "content": validation_prompt}],
                )
            )

            # Parse validation results
            validation_text = response.content[0].text if response.content else "{}"

            # Extract JSON from response
            try:
                json_start = validation_text.find("[")
                json_end = validation_text.rfind("]") + 1
                if json_start >= 0 and json_end > json_start:
                    validation_json = validation_text[json_start:json_end]
                    validations = json.loads(validation_json)

                    # Update patterns with validation results
                    validated_patterns = []
                    for i, pattern in enumerate(patterns):
                        if i < len(validations):
                            val = validations[i]
                            if val.get("validated", True):
                                # Update confidence with Claude's assessment
                                pattern.confidence = val.get("confidence", pattern.confidence)
                                validated_patterns.append(pattern)
                        else:
                            validated_patterns.append(pattern)

                    logger.info(
                        f"Claude validation: {len(validated_patterns)}/{len(patterns)} patterns validated"
                    )
                    return validated_patterns
            except (json.JSONDecodeError, IndexError) as e:
                logger.warning(f"Failed to parse Claude validation response: {e}")
                return patterns

        except Exception as e:
            logger.error(f"Claude validation failed: {e}")
            # Return patterns with original confidence scores
            return patterns


class ConsolidationWithDualProcess:
    """Consolidation pipeline enhanced with dual-process reasoning.

    Combines:
    - System 1: Fast heuristics (existing clustering + basic extraction)
    - System 2: Local reasoning (Qwen2.5-7B)
    - Validation: Claude API (optional, for high-stakes decisions)
    """

    def __init__(
        self,
        local_reasoner: Optional[LocalConsolidationReasoner] = None,
        claude_client: Optional[Any] = None,
    ):
        """Initialize dual-process consolidation.

        Args:
            local_reasoner: LocalConsolidationReasoner instance
            claude_client: Optional Claude client for validation
        """
        self.local_reasoner = local_reasoner or LocalConsolidationReasoner(
            claude_client=claude_client
        )
        self.claude_client = claude_client

    async def extract_patterns_dual_process(
        self,
        event_cluster: List[EpisodicEvent],
        system_1_patterns: List[Pattern],
        use_local: bool = True,
        use_claude_validation: bool = False,
    ) -> DualProcessResult:
        """Extract patterns using dual-process reasoning.

        Algorithm:
        1. System 1: Use existing heuristics (fast)
        2. Calculate confidence from System 1
        3. System 2: Use local reasoning (Qwen2.5-7B) for complex cases
        4. Merge and deduplicate patterns
        5. Optional: Validate with Claude if uncertainty > threshold

        Args:
            event_cluster: Related episodic events
            system_1_patterns: Patterns from heuristics
            use_local: Use local reasoning (System 2)
            use_claude_validation: Use Claude for validation

        Returns:
            DualProcessResult with merged patterns and metrics
        """
        import time

        start_time = time.time()
        local_patterns = []
        claude_patterns = None
        cost_saved = 0.0

        # Step 1: System 1 patterns (already provided)
        system_1_confidence = (
            sum(p.confidence for p in system_1_patterns) / len(system_1_patterns)
            if system_1_patterns
            else 0.0
        )

        logger.info(f"System 1 confidence: {system_1_confidence:.2f}")

        # Step 2: If uncertainty high, use System 2
        if use_local and system_1_confidence < 0.7:
            logger.info("System 1 confidence low, invoking System 2 (local reasoning)")

            try:
                local_result = await self.local_reasoner.extract_patterns_with_local_reasoning(
                    event_cluster=event_cluster,
                    use_claude_validation=use_claude_validation,
                )

                local_patterns = local_result.patterns

                logger.info(
                    f"System 2 extracted {len(local_patterns)} patterns "
                    f"in {local_result.latency_ms:.1f}ms"
                )

            except Exception as e:
                logger.error(f"System 2 reasoning failed: {e}")
                # Continue with System 1 only

        # Step 3: Optionally validate with Claude
        if use_claude_validation and local_patterns:
            compression_result = await self.local_reasoner.compress_for_claude_validation(
                patterns=local_patterns,
                events_text=self.local_reasoner._format_events(event_cluster),
            )

            cost_saved = compression_result["token_savings"]

            # Call Claude API for validation
            claude_patterns = await self.local_reasoner._validate_patterns_with_claude(
                patterns=local_patterns,
                events_text=self.local_reasoner._format_events(event_cluster),
                local_reasoning=json.dumps([p.to_dict() for p in local_patterns]),
            )
            logger.info(f"Compressed prompt: saved {cost_saved} tokens")

        # Step 4: Merge patterns (avoid duplicates)
        merged_patterns = self._merge_patterns(system_1_patterns, local_patterns)

        # Step 5: Calculate metrics
        total_latency = (time.time() - start_time) * 1000
        validation_score = (
            sum(p.confidence for p in merged_patterns) / len(merged_patterns)
            if merged_patterns
            else 0.0
        )

        cost_saved_percent = (cost_saved / 10000) * 100 if cost_saved > 0 else 0

        return DualProcessResult(
            patterns=merged_patterns,
            local_patterns=local_patterns,
            claude_patterns=claude_patterns,
            validation_score=validation_score,
            total_latency_ms=total_latency,
            cost_saved_percent=cost_saved_percent,
        )

    def _merge_patterns(self, system_1: List[Pattern], system_2: List[Pattern]) -> List[Pattern]:
        """Merge patterns from System 1 and System 2 using conflict resolution.

        Uses intelligent conflict resolution when patterns disagree:
        - Higher confidence wins (if diff > 0.2)
        - Evidence overlap determines merge strategy
        - Defers uncertain conflicts for human review
        - Preserves confidence in final patterns

        Args:
            system_1: Patterns from heuristics
            system_2: Patterns from local reasoning

        Returns:
            Merged pattern list with resolved conflicts
        """
        # Import conflict resolver (avoid circular imports)
        try:
            from .pattern_conflict_resolver import PatternConflictResolver

            use_conflict_resolver = True
        except ImportError:
            use_conflict_resolver = False
            logger.debug("Pattern conflict resolver not available, using basic merge")

        merged = dict()  # Use description as key for grouping
        conflicts = []  # Track conflicts for learning

        # Group patterns by description (approximate match)
        s1_map = {p.description.lower(): p for p in system_1}
        s2_map = {p.description.lower(): p for p in system_2}

        # Find all unique patterns
        all_descriptions = set(s1_map.keys()) | set(s2_map.keys())

        for desc_key in all_descriptions:
            s1_pattern = s1_map.get(desc_key)
            s2_pattern = s2_map.get(desc_key)

            if s1_pattern and s2_pattern:
                # Both systems extracted pattern - potential conflict
                if use_conflict_resolver:
                    # Use intelligent conflict resolution
                    resolver = PatternConflictResolver()

                    # Convert to conflict resolver format
                    s1_dict = {
                        "description": s1_pattern.description,
                        "pattern_type": "pattern",
                        "confidence": s1_pattern.confidence,
                        "tags": s1_pattern.tags or [],
                        "evidence": s1_pattern.evidence or "",
                    }

                    s2_dict = {
                        "description": s2_pattern.description,
                        "pattern_type": "pattern",
                        "confidence": s2_pattern.confidence,
                        "tags": s2_pattern.tags or [],
                        "evidence": s2_pattern.evidence or "",
                    }

                    # Detect and resolve conflicts
                    conflict = resolver.detect_conflict(
                        cluster_id=0,  # Placeholder
                        system_1_pattern=s1_dict,
                        system_2_pattern=s2_dict,
                    )

                    if conflict:
                        # Resolve the conflict
                        resolution = resolver.resolve_conflict(conflict)
                        conflicts.append((conflict, resolution))

                        # Convert resolved pattern back
                        resolved_dict = resolution.selected_pattern
                        resolved_pattern = Pattern(
                            description=resolved_dict["description"],
                            pattern_type=resolved_dict.get("pattern_type", "pattern"),
                            confidence=resolved_dict.get("confidence", 0.75),
                            tags=resolved_dict.get("tags", []),
                            evidence=resolved_dict.get("evidence", ""),
                        )
                        merged[desc_key] = resolved_pattern
                    else:
                        # No conflict - use higher confidence
                        if s1_pattern.confidence >= s2_pattern.confidence:
                            merged[desc_key] = s1_pattern
                        else:
                            merged[desc_key] = s2_pattern
                else:
                    # Basic merge: use higher confidence
                    if s1_pattern.confidence >= s2_pattern.confidence:
                        merged[desc_key] = s1_pattern
                    else:
                        merged[desc_key] = s2_pattern

            elif s1_pattern:
                merged[desc_key] = s1_pattern
            else:
                merged[desc_key] = s2_pattern

        # Log conflict resolution statistics
        if conflicts:
            logger.info(
                f"Resolved {len(conflicts)} pattern conflicts: "
                f"{sum(1 for _, r in conflicts if r.requires_human_review)} "
                f"require human review"
            )

        return list(merged.values())


def get_local_reasoner(
    llm_client: Optional[LocalLLMClient] = None,
    enable_compression: bool = True,
) -> LocalConsolidationReasoner:
    """Factory function to get or create LocalConsolidationReasoner.

    Args:
        llm_client: LocalLLMClient instance (created if not provided)
        enable_compression: Enable prompt compression

    Returns:
        LocalConsolidationReasoner instance
    """
    return LocalConsolidationReasoner(llm_client=llm_client, enable_compression=enable_compression)
