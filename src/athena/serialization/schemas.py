"""TOON schema definitions for Athena data types.

Defines field ordering and type hints for TOON-encoded data structures.
"""

from typing import Dict, List

# Schema format: field_name -> type_hint
# Used for TOON header generation and validation

TOON_SCHEMAS: Dict[str, Dict[str, List[str]]] = {
    # Episodic Memory Events
    "episodic_events": {
        "fields": [
            "id",
            "type",
            "timestamp",
            "tags",
            "entity_type",
            "entity_name",
            "relevance_score",
        ],
        "types": {
            "id": "int",
            "type": "str",
            "timestamp": "str",
            "tags": "array",
            "entity_type": "str",
            "entity_name": "str",
            "relevance_score": "float",
        },
        "description": "Episodic memory events with temporal grounding",
    },
    # Knowledge Graph Entities
    "knowledge_graph_entities": {
        "fields": ["id", "type", "name", "domain", "salience", "community_id"],
        "types": {
            "id": "int",
            "type": "str",
            "name": "str",
            "domain": "str",
            "salience": "float",
            "community_id": "int",
        },
        "description": "Knowledge graph entities with type and domain",
    },
    # Knowledge Graph Relations
    "knowledge_graph_relations": {
        "fields": ["id", "source_id", "target_id", "relation_type", "weight", "context"],
        "types": {
            "id": "int",
            "source_id": "int",
            "target_id": "int",
            "relation_type": "str",
            "weight": "float",
            "context": "str",
        },
        "description": "Knowledge graph relations between entities",
    },
    # Semantic Search Results
    "semantic_search_results": {
        "fields": ["rank", "score", "id", "text_preview", "source_type", "timestamp"],
        "types": {
            "rank": "int",
            "score": "float",
            "id": "int",
            "text_preview": "str",
            "source_type": "str",
            "timestamp": "str",
        },
        "description": "Semantic search results with relevance scores",
    },
    # Procedural Memory - Procedures
    "procedures_list": {
        "fields": [
            "id",
            "name",
            "category",
            "steps_count",
            "effectiveness_score",
            "uses_count",
            "last_used",
        ],
        "types": {
            "id": "int",
            "name": "str",
            "category": "str",
            "steps_count": "int",
            "effectiveness_score": "float",
            "uses_count": "int",
            "last_used": "str",
        },
        "description": "Learned procedures with effectiveness metrics",
    },
    # Procedural Memory - Procedure Steps
    "procedure_steps": {
        "fields": ["order", "action", "input_spec", "output_spec", "confidence"],
        "types": {
            "order": "int",
            "action": "str",
            "input_spec": "str",
            "output_spec": "str",
            "confidence": "float",
        },
        "description": "Steps within a learned procedure",
    },
    # Meta-Memory Quality Metrics
    "memory_layer_metrics": {
        "fields": ["layer_name", "event_count", "quality_score", "compression_ratio"],
        "types": {
            "layer_name": "str",
            "event_count": "int",
            "quality_score": "float",
            "compression_ratio": "float",
        },
        "description": "Memory layer health and quality metrics",
    },
    # Prospective Memory - Tasks
    "tasks_list": {
        "fields": [
            "id",
            "title",
            "status",
            "priority",
            "created_at",
            "due_date",
            "progress_percent",
        ],
        "types": {
            "id": "int",
            "title": "str",
            "status": "str",
            "priority": "str",
            "created_at": "str",
            "due_date": "str",
            "progress_percent": "int",
        },
        "description": "Task list with status and progress",
    },
    # Prospective Memory - Goals
    "goals_list": {
        "fields": ["id", "name", "status", "priority", "deadline", "completion_percent"],
        "types": {
            "id": "int",
            "name": "str",
            "status": "str",
            "priority": "str",
            "deadline": "str",
            "completion_percent": "int",
        },
        "description": "Goals with lifecycle tracking",
    },
    # System Health Report
    "system_health": {
        "fields": ["component", "status", "uptime_percent", "error_count", "latency_ms"],
        "types": {
            "component": "str",
            "status": "str",
            "uptime_percent": "float",
            "error_count": "int",
            "latency_ms": "float",
        },
        "description": "System health and performance metrics",
    },
    # RAG Context Items
    "rag_context_items": {
        "fields": ["rank", "relevance_score", "source", "content_preview", "metadata"],
        "types": {
            "rank": "int",
            "relevance_score": "float",
            "source": "str",
            "content_preview": "str",
            "metadata": "str",
        },
        "description": "Retrieved context items from RAG operations",
    },
    # Consolidation Patterns
    "consolidation_patterns": {
        "fields": [
            "id",
            "pattern_type",
            "frequency",
            "confidence",
            "created_at",
            "description",
        ],
        "types": {
            "id": "int",
            "pattern_type": "str",
            "frequency": "int",
            "confidence": "float",
            "created_at": "str",
            "description": "str",
        },
        "description": "Extracted patterns from consolidation",
    },
    # Working Memory Items
    "working_memory_items": {
        "fields": ["id", "content", "recency_score", "activation", "relevance"],
        "types": {
            "id": "int",
            "content": "str",
            "recency_score": "float",
            "activation": "float",
            "relevance": "float",
        },
        "description": "Working memory (7±2) active items",
    },
}


def get_schema(schema_name: str) -> Dict:
    """Get schema definition by name.

    Args:
        schema_name: Name of schema (e.g., 'episodic_events')

    Returns:
        Schema dictionary with fields, types, description

    Raises:
        KeyError: If schema not found
    """
    if schema_name not in TOON_SCHEMAS:
        raise KeyError(f"Unknown schema: {schema_name}. Available: {list(TOON_SCHEMAS.keys())}")
    return TOON_SCHEMAS[schema_name]


def get_field_order(schema_name: str) -> List[str]:
    """Get field ordering for schema.

    Args:
        schema_name: Name of schema

    Returns:
        List of field names in order

    Raises:
        KeyError: If schema not found
    """
    schema = get_schema(schema_name)
    return schema["fields"]


def validate_against_schema(data: Dict, schema_name: str) -> bool:
    """Validate data matches schema structure.

    Args:
        data: Dictionary to validate
        schema_name: Schema name to validate against

    Returns:
        True if data matches schema, False otherwise
    """
    try:
        schema = get_schema(schema_name)
        required_fields = set(schema["fields"])

        if isinstance(data, dict):
            # For single objects, check if all fields present
            return all(field in data for field in required_fields)
        elif isinstance(data, list):
            # For arrays, check first element
            return all(all(field in item for field in required_fields) for item in data[:1])

        return False
    except KeyError:
        return False


def describe_schema(schema_name: str) -> str:
    """Get human-readable schema description.

    Args:
        schema_name: Schema name

    Returns:
        Description string

    Raises:
        KeyError: If schema not found
    """
    schema = get_schema(schema_name)
    fields = ", ".join(schema["fields"])
    return f"{schema['description']}\nFields: {fields}"
