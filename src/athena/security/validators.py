"""Input validation for Athena MCP tools (Phase 3).

Validates:
- String lengths (queries max 10KB)
- Integer bounds (limits 1-1000)
- Enum values (memory_type, priority, status)
- Regex patterns (no SQL injection patterns)
- Project IDs and entity names
"""

import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, validator, ValidationError


class ValidationError(Exception):
    """Custom validation error."""
    pass


class RecallRequest(BaseModel):
    """Validated recall request."""

    project_id: str = Field(..., min_length=1, max_length=100)
    query: str = Field(..., min_length=1, max_length=10000)
    limit: int = Field(default=10, ge=1, le=1000)

    @validator('project_id')
    def project_id_valid(cls, v):
        """Validate project ID format."""
        if not re.match(r'^[a-zA-Z0-9_\-]+$', v):
            raise ValueError("Project ID contains invalid characters")
        return v

    @validator('query')
    def query_no_injection(cls, v):
        """Validate query doesn't contain SQL injection patterns."""
        dangerous_patterns = [
            r'(?i)drop\s+table',
            r'(?i)delete\s+from',
            r'(?i)insert\s+into',
            r'(?i)union\s+select',
            r'(?i)exec\s*\(',
            r'(?i)execute\s*\(',
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, v):
                raise ValueError(f"Query contains potentially dangerous pattern: {pattern}")

        return v


class RememberRequest(BaseModel):
    """Validated remember request."""

    project_id: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1, max_length=50000)
    memory_type: str = Field(..., regex=r'^(fact|pattern|decision|context)$')

    @validator('project_id')
    def project_id_valid(cls, v):
        """Validate project ID format."""
        if not re.match(r'^[a-zA-Z0-9_\-]+$', v):
            raise ValueError("Project ID contains invalid characters")
        return v


class CreateTaskRequest(BaseModel):
    """Validated create task request."""

    project_id: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = Field(default=None, max_length=5000)
    priority: str = Field(default="medium", regex=r'^(low|medium|high|critical)$')
    status: str = Field(default="pending", regex=r'^(pending|in_progress|completed|paused|cancelled)$')

    @validator('project_id')
    def project_id_valid(cls, v):
        """Validate project ID."""
        if not re.match(r'^[a-zA-Z0-9_\-]+$', v):
            raise ValueError("Invalid project ID")
        return v


class CreateEntityRequest(BaseModel):
    """Validated create entity request."""

    project_id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=500)
    entity_type: str = Field(...)
    description: Optional[str] = Field(default=None, max_length=5000)

    @validator('project_id')
    def project_id_valid(cls, v):
        """Validate project ID."""
        if not re.match(r'^[a-zA-Z0-9_\-]+$', v):
            raise ValueError("Invalid project ID")
        return v

    @validator('name')
    def name_no_injection(cls, v):
        """Validate name for XSS/injection."""
        if re.search(r'[<>"\';]', v):
            raise ValueError("Name contains potentially dangerous characters")
        return v


class CreateRelationRequest(BaseModel):
    """Validated create relation request."""

    project_id: str = Field(..., min_length=1, max_length=100)
    source_name: str = Field(..., min_length=1, max_length=500)
    target_name: str = Field(..., min_length=1, max_length=500)
    relation_type: str = Field(..., min_length=1, max_length=100)

    @validator('project_id')
    def project_id_valid(cls, v):
        """Validate project ID."""
        if not re.match(r'^[a-zA-Z0-9_\-]+$', v):
            raise ValueError("Invalid project ID")
        return v


class RecordEventRequest(BaseModel):
    """Validated record event request."""

    project_id: str = Field(..., min_length=1, max_length=100)
    event_type: str = Field(..., min_length=1, max_length=50)
    description: str = Field(..., min_length=1, max_length=5000)
    context: Optional[Dict[str, Any]] = Field(default=None)

    @validator('project_id')
    def project_id_valid(cls, v):
        """Validate project ID."""
        if not re.match(r'^[a-zA-Z0-9_\-]+$', v):
            raise ValueError("Invalid project ID")
        return v

    @validator('context')
    def context_not_huge(cls, v):
        """Limit context size."""
        if v and len(str(v)) > 10000:
            raise ValueError("Context too large (max 10KB)")
        return v


# Validation functions for direct use

def validate_project_id(project_id: str) -> str:
    """Validate project ID.

    Args:
        project_id: Project identifier

    Returns:
        Validated project ID

    Raises:
        ValidationError: If invalid
    """
    if not project_id or len(project_id) > 100:
        raise ValidationError("Invalid project ID length")

    if not re.match(r'^[a-zA-Z0-9_\-]+$', project_id):
        raise ValidationError("Project ID contains invalid characters")

    return project_id


def validate_query(query: str, max_length: int = 10000) -> str:
    """Validate query string.

    Args:
        query: Query string
        max_length: Maximum length

    Returns:
        Validated query

    Raises:
        ValidationError: If invalid
    """
    if not query or len(query) > max_length:
        raise ValidationError(f"Query length invalid (max {max_length})")

    # Check for SQL injection patterns
    dangerous_patterns = [
        r'(?i)drop\s+table',
        r'(?i)delete\s+from',
        r'(?i)insert\s+into',
        r'(?i)union\s+select',
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, query):
            raise ValidationError("Query contains potentially dangerous pattern")

    return query


def validate_memory_type(memory_type: str) -> str:
    """Validate memory type.

    Args:
        memory_type: Memory type (fact, pattern, decision, context)

    Returns:
        Validated memory type

    Raises:
        ValidationError: If invalid
    """
    valid_types = {'fact', 'pattern', 'decision', 'context'}

    if memory_type not in valid_types:
        raise ValidationError(f"Invalid memory type. Must be one of: {', '.join(valid_types)}")

    return memory_type


def validate_priority(priority: str) -> str:
    """Validate task priority.

    Args:
        priority: Priority level

    Returns:
        Validated priority

    Raises:
        ValidationError: If invalid
    """
    valid_priorities = {'low', 'medium', 'high', 'critical'}

    if priority not in valid_priorities:
        raise ValidationError(f"Invalid priority. Must be one of: {', '.join(valid_priorities)}")

    return priority


def validate_limit(limit: int, max_limit: int = 1000) -> int:
    """Validate result limit.

    Args:
        limit: Result limit
        max_limit: Maximum allowed limit

    Returns:
        Validated limit

    Raises:
        ValidationError: If invalid
    """
    if not isinstance(limit, int):
        raise ValidationError("Limit must be an integer")

    if limit < 1 or limit > max_limit:
        raise ValidationError(f"Limit must be between 1 and {max_limit}")

    return limit


def validate_entity_name(name: str) -> str:
    """Validate entity name.

    Args:
        name: Entity name

    Returns:
        Validated name

    Raises:
        ValidationError: If invalid
    """
    if not name or len(name) > 500:
        raise ValidationError("Entity name invalid length")

    if re.search(r'[<>"\';]', name):
        raise ValidationError("Entity name contains dangerous characters")

    return name


def validate_all(request_dict: Dict[str, Any], request_class: type) -> Dict[str, Any]:
    """Validate all request fields.

    Args:
        request_dict: Request data
        request_class: Pydantic request class

    Returns:
        Validated data

    Raises:
        ValidationError: If validation fails
    """
    try:
        request = request_class(**request_dict)
        return request.dict()
    except ValidationError as e:
        raise ValidationError(f"Validation failed: {e}")
