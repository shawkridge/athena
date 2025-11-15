# Consolidation Tools

## consolidate
- **Description**: Extract patterns from episodic events (sleep-like consolidation)
- **Entry Point**: `consolidate()`
- **Returns**: ConsolidationReport - Patterns extracted and quality metrics
- **Example**: `consolidate(strategy='quality')`

## get_patterns
- **Description**: Retrieve learned patterns from consolidation
- **Entry Point**: `get_patterns()`
- **Returns**: List[Pattern] - Learned patterns with confidence scores
- **Example**: `get_patterns(domain='security', limit=5)`
