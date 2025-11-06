"""External knowledge integration module.

This module provides access to external knowledge sources:
- ConceptNet API for common-sense knowledge (21M+ relations)
- Wikidata API for structured knowledge
- Wikipedia integration for articles and summaries
"""

from .conceptnet_api import ConceptNetAPI

__all__ = [
    "ConceptNetAPI",
]
