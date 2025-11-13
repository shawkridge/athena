"""Extract patterns from consolidated memories tool."""
import time
from typing import Any, Dict
from athena.tools import BaseTool, ToolMetadata


class ExtractPatternsTool(BaseTool):
    """Tool for extracting patterns from consolidated memories.

    Analyzes consolidated memories to identify statistical patterns,
    causal relationships, and temporal sequences. Supports multiple
    pattern types and filtering.

    Example:
        >>> tool = ExtractPatternsTool()
        >>> result = await tool.execute(
        ...     pattern_type="statistical",
        ...     min_frequency=3,
        ...     max_patterns=50
        ... )
    """

    def __init__(self):
        """Initialize pattern extraction tool."""
        self._manager = None

    @property
    def metadata(self) -> ToolMetadata:
        """Return tool metadata."""
        return ToolMetadata(
            name="consolidation_extract",
            category="consolidation",
            description="Extract patterns from consolidated memories",
            parameters={
                "pattern_type": {
                    "type": "string",
                    "enum": ["statistical", "causal", "temporal", "all"],
                    "description": "Type of patterns to extract",
                    "required": False,
                    "default": "all"
                },
                "min_frequency": {
                    "type": "integer",
                    "description": "Minimum frequency for pattern detection",
                    "required": False,
                    "default": 3,
                    "minimum": 1,
                    "maximum": 1000
                },
                "max_patterns": {
                    "type": "integer",
                    "description": "Maximum patterns to extract",
                    "required": False,
                    "default": 100,
                    "minimum": 1,
                    "maximum": 10000
                },
                "confidence_threshold": {
                    "type": "number",
                    "description": "Minimum confidence score (0-1)",
                    "required": False,
                    "default": 0.6,
                    "minimum": 0.0,
                    "maximum": 1.0
                }
            },
            returns={
                "type": "object",
                "properties": {
                    "patterns_found": {
                        "type": "integer",
                        "description": "Number of patterns extracted"
                    },
                    "pattern_type": {
                        "type": "string",
                        "description": "Type of patterns extracted"
                    },
                    "patterns": {
                        "type": "array",
                        "description": "List of extracted patterns",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "type": {"type": "string"},
                                "description": {"type": "string"},
                                "frequency": {"type": "integer"},
                                "confidence": {"type": "number"}
                            }
                        }
                    },
                    "extraction_time_ms": {
                        "type": "number",
                        "description": "Time taken to extract patterns"
                    }
                }
            }
        )

    def validate_input(self, **kwargs) -> None:
        """Validate input parameters."""
        if "pattern_type" in kwargs:
            valid = {"statistical", "causal", "temporal", "all"}
            if kwargs["pattern_type"] not in valid:
                raise ValueError(f"pattern_type must be one of: {', '.join(sorted(valid))}")

        if "min_frequency" in kwargs:
            freq = kwargs["min_frequency"]
            if not isinstance(freq, int) or freq < 1 or freq > 1000:
                raise ValueError("min_frequency must be between 1 and 1000")

        if "max_patterns" in kwargs:
            max_p = kwargs["max_patterns"]
            if not isinstance(max_p, int) or max_p < 1 or max_p > 10000:
                raise ValueError("max_patterns must be between 1 and 10,000")

        if "confidence_threshold" in kwargs:
            conf = kwargs["confidence_threshold"]
            if not isinstance(conf, (int, float)) or not (0.0 <= conf <= 1.0):
                raise ValueError("confidence_threshold must be between 0.0 and 1.0")

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute pattern extraction."""
        start_time = time.time()

        try:
            self.validate_input(**kwargs)

            pattern_type = kwargs.get("pattern_type", "all")
            min_frequency = kwargs.get("min_frequency", 3)
            max_patterns = kwargs.get("max_patterns", 100)
            confidence_threshold = kwargs.get("confidence_threshold", 0.6)

            # Implement actual pattern extraction from episodic events
            patterns = []
            patterns_found = 0

            try:
                from athena.core.database import get_database
                db = get_database()

                try:
                    cursor = db.conn.cursor()

                    # Get recent episodic events for pattern extraction
                    cursor.execute(
                        """SELECT id, timestamp, content, event_type, tags
                           FROM episodic_events
                           ORDER BY timestamp DESC
                           LIMIT ?""",
                        (max_events,)
                    )
                    rows = cursor.fetchall()

                    if rows:
                        # Extract patterns based on type
                        if pattern_type == "statistical":
                            # Extract statistical patterns (frequency-based)
                            content_words = {}
                            for row in rows:
                                content = row[2]
                                words = content.lower().split()
                                for word in words:
                                    if len(word) > 5:  # Filter short words
                                        content_words[word] = content_words.get(word, 0) + 1

                            # Find frequent patterns
                            for word, freq in sorted(content_words.items(), key=lambda x: x[1], reverse=True)[:5]:
                                if freq >= min_frequency:
                                    confidence = min(1.0, freq / len(rows))
                                    if confidence >= confidence_threshold:
                                        patterns.append({
                                            "pattern": word,
                                            "type": "keyword",
                                            "frequency": freq,
                                            "confidence": confidence
                                        })

                        elif pattern_type == "causal":
                            # Extract causal patterns (event sequences)
                            for i in range(len(rows) - 1):
                                if rows[i][3] == rows[i + 1][3]:  # Same event type
                                    patterns.append({
                                        "pattern": f"{rows[i][3]} → {rows[i + 1][3]}",
                                        "type": "causal",
                                        "confidence": 0.7,
                                        "events": [rows[i][0], rows[i + 1][0]]
                                    })

                        elif pattern_type == "temporal":
                            # Extract temporal patterns (periodic occurrences)
                            event_times = {}
                            for row in rows:
                                event_type = row[3]
                                if event_type not in event_times:
                                    event_times[event_type] = []
                                event_times[event_type].append(row[1])

                            for event_type, times in event_times.items():
                                if len(times) >= min_frequency:
                                    patterns.append({
                                        "pattern": f"Periodic {event_type}",
                                        "type": "temporal",
                                        "frequency": len(times),
                                        "confidence": min(1.0, len(times) / len(rows))
                                    })

                        else:
                            # Default: statistical
                            content_words = {}
                            for row in rows:
                                content = row[2]
                                words = content.lower().split()
                                for word in words:
                                    if len(word) > 5:
                                        content_words[word] = content_words.get(word, 0) + 1

                            for word, freq in sorted(content_words.items(), key=lambda x: x[1], reverse=True)[:5]:
                                if freq >= min_frequency:
                                    confidence = min(1.0, freq / len(rows))
                                    if confidence >= confidence_threshold:
                                        patterns.append({
                                            "pattern": word,
                                            "type": "keyword",
                                            "frequency": freq,
                                            "confidence": confidence
                                        })

                        patterns_found = len(patterns)

                except Exception as db_err:
                    import logging
                    logging.warning(f"Pattern extraction query failed: {db_err}")

            except Exception as e:
                import logging
                logging.debug(f"Pattern extraction unavailable: {e}")

            elapsed = (time.time() - start_time) * 1000

            return {
                "patterns_found": patterns_found,
                "pattern_type": pattern_type,
                "patterns": patterns,
                "min_frequency": min_frequency,
                "confidence_threshold": confidence_threshold,
                "max_events_analyzed": max_events,
                "extraction_time_ms": elapsed,
                "status": "success"
            }

        except ValueError as e:
            return {
                "error": str(e),
                "status": "error",
                "extraction_time_ms": (time.time() - start_time) * 1000
            }
        except Exception as e:
            return {
                "error": f"Unexpected error: {str(e)}",
                "status": "error",
                "extraction_time_ms": (time.time() - start_time) * 1000
            }
