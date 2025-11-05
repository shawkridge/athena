"""Utility functions for working memory operations."""

import pickle
from typing import List


def serialize_embedding(embedding: List[float]) -> bytes:
    """Serialize embedding vector to bytes.

    Args:
        embedding: Embedding vector as list of floats

    Returns:
        Serialized embedding as bytes
    """
    return pickle.dumps(embedding)


def deserialize_embedding(embedding_bytes: bytes) -> List[float]:
    """Deserialize embedding vector from bytes.

    Args:
        embedding_bytes: Serialized embedding bytes

    Returns:
        Embedding vector as list of floats
    """
    return pickle.loads(embedding_bytes)
