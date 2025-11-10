"""TOON integration utilities for MCP handlers.

Provides easy integration of TOON format into existing handlers
with automatic format selection and fallback to JSON.
"""

import json
import logging
import time
from typing import Any, Dict, Optional, Union

from athena.core import config
from athena.serialization.toon_codec import TOONCodec, TOONCodecError
from athena.serialization.metrics import record_encode_metric

logger = logging.getLogger(__name__)


class TOONIntegrator:
    """Integration helper for TOON format in handlers."""

    @staticmethod
    def should_use_toon(
        data_type: Optional[str] = None,
        data_size_bytes: Optional[int] = None,
    ) -> bool:
        """Determine if TOON should be used for given data.

        Args:
            data_type: Type of data (episodic_events, semantic_search_results, etc)
            data_size_bytes: Size of data in bytes

        Returns:
            True if TOON should be used, False otherwise
        """
        if not config.ENABLE_TOON_FORMAT:
            return False

        # Check specific data type config
        type_config_map = {
            "episodic_events": config.TOON_USE_EPISODIC_EVENTS,
            "knowledge_graph": config.TOON_USE_KNOWLEDGE_GRAPH,
            "procedural": config.TOON_USE_PROCEDURAL,
            "semantic_search": config.TOON_USE_SEMANTIC_SEARCH,
            "metrics": config.TOON_USE_METRICS,
        }

        if data_type and data_type in type_config_map:
            if not type_config_map[data_type]:
                return False

        # Don't use TOON for very small payloads
        if data_size_bytes and data_size_bytes < 200:
            return False

        return True

    @staticmethod
    def serialize(
        data: Union[Dict, list],
        schema_name: Optional[str] = None,
        use_toon: Optional[bool] = None,
    ) -> str:
        """Serialize data to TOON or JSON.

        Args:
            data: Data to serialize (dict or list)
            schema_name: TOON schema name for encoding
            use_toon: Override default TOON usage. If None, auto-decides.

        Returns:
            Serialized string (TOON or JSON)
        """
        if not data:
            return "{}"

        # Decide format
        if use_toon is None:
            json_str = json.dumps(data)
            use_toon = TOONIntegrator.should_use_toon(
                data_type=schema_name,
                data_size_bytes=len(json_str.encode("utf-8")),
            )
        else:
            json_str = json.dumps(data)

        # Use TOON if requested and available
        if use_toon and TOONCodec.is_available():
            try:
                start_time = time.time()
                toon_str = TOONCodec.encode(data, timeout=config.TOON_ENCODING_TIMEOUT)
                duration_ms = (time.time() - start_time) * 1000

                # Record metrics
                record_encode_metric(
                    schema_name or "unknown",
                    duration_ms,
                    json_str,
                    toon_str,
                    success=True,
                )

                return toon_str

            except TOONCodecError as e:
                logger.warning(f"TOON encoding failed: {e}")
                if config.TOON_FALLBACK_TO_JSON:
                    logger.debug("Falling back to JSON")
                    record_encode_metric(
                        schema_name or "unknown",
                        0,
                        json_str,
                        "",
                        success=False,
                        error=str(e),
                    )
                    return json_str
                raise

        # Default to JSON
        return json_str

    @staticmethod
    def serialize_search_results(
        results: list,
        limit: int = 10,
        use_toon: Optional[bool] = None,
    ) -> str:
        """Serialize semantic search results.

        Args:
            results: Search result dictionaries
            limit: Result limit used
            use_toon: Override TOON usage

        Returns:
            Serialized results (TOON or JSON)
        """
        data = {"results": results, "limit": limit, "count": len(results)}
        return TOONIntegrator.serialize(
            data, schema_name="semantic_search_results", use_toon=use_toon
        )

    @staticmethod
    def serialize_episodic_events(
        events: list,
        use_toon: Optional[bool] = None,
    ) -> str:
        """Serialize episodic memory events.

        Args:
            events: Event dictionaries
            use_toon: Override TOON usage

        Returns:
            Serialized events (TOON or JSON)
        """
        data = {"events": events, "count": len(events)}
        return TOONIntegrator.serialize(
            data, schema_name="episodic_events", use_toon=use_toon
        )

    @staticmethod
    def serialize_knowledge_graph_entities(
        entities: list,
        use_toon: Optional[bool] = None,
    ) -> str:
        """Serialize knowledge graph entities.

        Args:
            entities: Entity dictionaries
            use_toon: Override TOON usage

        Returns:
            Serialized entities (TOON or JSON)
        """
        data = {"entities": entities, "count": len(entities)}
        return TOONIntegrator.serialize(
            data, schema_name="knowledge_graph_entities", use_toon=use_toon
        )

    @staticmethod
    def serialize_procedures(
        procedures: list,
        use_toon: Optional[bool] = None,
    ) -> str:
        """Serialize procedural memory items.

        Args:
            procedures: Procedure dictionaries
            use_toon: Override TOON usage

        Returns:
            Serialized procedures (TOON or JSON)
        """
        data = {"procedures": procedures, "count": len(procedures)}
        return TOONIntegrator.serialize(
            data, schema_name="procedures_list", use_toon=use_toon
        )

    @staticmethod
    def serialize_metrics(
        metrics: Dict[str, Any],
        use_toon: Optional[bool] = None,
    ) -> str:
        """Serialize system metrics.

        Args:
            metrics: Metric dictionaries
            use_toon: Override TOON usage

        Returns:
            Serialized metrics (TOON or JSON)
        """
        return TOONIntegrator.serialize(
            metrics, schema_name="memory_layer_metrics", use_toon=use_toon
        )

    @staticmethod
    def wrap_handler_response(
        handler_name: str,
        data: Union[Dict, list],
        schema_name: Optional[str] = None,
    ) -> str:
        """Wrap handler response with TOON serialization.

        Usage in handlers:
            results = query_results()
            response_text = TOONIntegrator.wrap_handler_response(
                "recall",
                results,
                schema_name="episodic_events"
            )
            return [TextContent(type="text", text=response_text)]

        Args:
            handler_name: Name of handler (for logging)
            data: Data to serialize
            schema_name: Optional schema name

        Returns:
            Formatted response string
        """
        try:
            serialized = TOONIntegrator.serialize(data, schema_name=schema_name)

            # Format response based on format used
            if serialized.startswith("{"):
                # JSON or TOON starting with {
                format_marker = ""
                if TOONIntegrator.should_use_toon(schema_name) and TOONCodec.is_available():
                    # Try to detect if it's TOON by checking if it lacks typical JSON indicators
                    if (
                        "{" in serialized
                        and serialized.count("{") <= 2
                        and '"' not in serialized[: min(50, len(serialized))]
                    ):
                        format_marker = "[TOON Format] "

            else:
                format_marker = "[TOON Format] "

            return f"{format_marker}{serialized}"

        except Exception as e:
            logger.error(f"Error wrapping handler response ({handler_name}): {e}")
            # Fallback to plain JSON
            return json.dumps(data)

    @staticmethod
    def get_format_info() -> Dict[str, Any]:
        """Get information about current TOON format configuration.

        Returns:
            Dictionary with format information
        """
        return {
            "toon_enabled": config.ENABLE_TOON_FORMAT,
            "toon_available": TOONCodec.is_available(),
            "use_episodic_events": config.TOON_USE_EPISODIC_EVENTS,
            "use_knowledge_graph": config.TOON_USE_KNOWLEDGE_GRAPH,
            "use_procedural": config.TOON_USE_PROCEDURAL,
            "use_semantic_search": config.TOON_USE_SEMANTIC_SEARCH,
            "use_metrics": config.TOON_USE_METRICS,
            "encoding_timeout_s": config.TOON_ENCODING_TIMEOUT,
            "fallback_to_json": config.TOON_FALLBACK_TO_JSON,
            "min_token_savings_percent": config.TOON_MIN_TOKEN_SAVINGS,
        }
