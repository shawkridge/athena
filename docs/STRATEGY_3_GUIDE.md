# Strategy 3: Codebase Pattern Detection

## Overview

**Strategy 3** teaches AI to ground its understanding in the actual codebase by detecting duplicate and repeated code patterns. This prevents "reinventing the wheel" and identifies opportunities for consolidation and abstraction.

**Core Philosophy**: *Duplication is the enemy of maintainability.* By maintaining a catalog of code patterns and detecting duplicates, we can identify where code should be refactored into shared utilities.

---

## How It Works

### 1. Pattern Extraction

The `PatternDetector` analyzes Python files to extract structural patterns:

```python
from athena.learning.pattern_detector import PatternDetector

detector = PatternDetector()

# Analyze codebase for patterns
analysis = detector.analyze_codebase(["src/", "tests/"])
# Result:
# {
#     "total_files": 42,
#     "patterns_found": 156,
#     "duplicate_groups": 8,
#     "patterns": {...},
#     "duplicates": [...],
#     "recommendations": [...]
# }
```

Patterns include:
- **Functions**: Extracted from all files (with signatures)
- **Classes**: Extracted from all files (with docstrings)
- **Logic Patterns**: Normalized code blocks for similarity matching

### 2. Duplicate Detection

The system identifies similar code across files:

```python
# Find similar functions
similar = detector.find_similar_functions(
    function_code="""
def validate_email(email: str) -> bool:
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))
""",
    all_files=["src/validators/email.py", "src/utils/email.py"],
    similarity_threshold=0.8
)
```

Finds functions with similar:
- Names (handling different naming conventions)
- Signatures
- Logic flow

### 3. Duplicate Logic Finding

Identifies repeated code snippets across the codebase:

```python
# Find duplicate logic
code_snippet = """
if not data:
    return None
result = process(data)
return result
"""

duplicates = detector.find_duplicate_logic(
    code_snippet,
    ["src/", "tests/"]
)
# Result: locations where similar logic appears
```

---

## Core Classes

### PatternDetector

Main class for code pattern analysis:

```python
class PatternDetector:
    def analyze_codebase(self, file_paths: List[str]) -> Dict[str, Any]:
        """Analyze codebase for patterns and duplicates."""

    def find_similar_functions(
        self,
        function_code: str,
        all_files: List[str],
        similarity_threshold: float = 0.8,
    ) -> List[Dict[str, Any]]:
        """Find similar functions in codebase."""

    def find_duplicate_logic(
        self,
        code_snippet: str,
        all_files: List[str],
    ) -> List[Dict[str, Any]]:
        """Find duplicate logic in codebase."""

    def suggest_refactoring(
        self,
        duplicate_group: DuplicateGroup,
    ) -> Dict[str, Any]:
        """Suggest refactoring for duplicated code."""

    def get_pattern_statistics(self) -> Dict[str, Any]:
        """Get statistics about patterns found."""
```

### CodePattern

Represents a code pattern found in the codebase:

```python
@dataclass
class CodePattern:
    pattern_id: str                    # Unique identifier
    name: str                          # Function/class name
    description: str                   # Docstring or purpose
    locations: List[Dict[str, Any]]   # Files and line numbers
    frequency: int                     # How many times found
    pattern_type: str                  # function|class|logic
    similarity_score: float            # 0.0-1.0
```

### DuplicateGroup

Represents a group of duplicate code instances:

```python
@dataclass
class DuplicateGroup:
    group_id: str                      # Unique identifier
    description: str                   # What's duplicated
    duplicates: List[Dict[str, Any]]  # Locations
    similarity_percentage: float       # 0.0-100.0
    recommendation: str                # Suggested refactoring
```

---

## Usage Examples

### Example 1: Find Function Duplicates

```python
detector = PatternDetector()

# Analyze the codebase
analysis = detector.analyze_codebase(["src/"])

# Look for functions that appear multiple times
for pattern in analysis["patterns"].values():
    if pattern.frequency > 1 and pattern.pattern_type == "function":
        print(f"{pattern.name} appears {pattern.frequency} times:")
        for loc in pattern.locations:
            print(f"  - {loc['file']}")

        # Get refactoring suggestions
        # Extract from duplicates list for this pattern
```

### Example 2: Detect Duplicate Logic Patterns

```python
# Code snippet you want to check for duplicates
validation_code = """
if not email:
    return False
if '@' not in email:
    return False
if '.' not in email:
    return False
return True
"""

# Find similar validation logic
duplicates = detector.find_duplicate_logic(
    validation_code,
    ["src/validators/", "src/utils/"]
)

if duplicates:
    print(f"Found {len(duplicates)} instances of similar validation logic")
    print("Consider extracting to shared validation module")
```

### Example 3: Similar Function Discovery

```python
# You found this function and want to find similar implementations
function_code = """
def process_user_data(user_dict):
    if not user_dict:
        return None
    data = validate(user_dict)
    if not data:
        return None
    return transform(data)
"""

similar = detector.find_similar_functions(
    function_code,
    all_files=["src/processors/", "src/handlers/"],
    similarity_threshold=0.75
)

for func in similar:
    print(f"{func['function']} in {func['file']}: {func['similarity']*100:.1f}% similar")
```

### Example 4: Get Codebase Statistics

```python
# Extract patterns first
patterns = detector._extract_patterns(all_files)
duplicates = detector._find_duplicates(patterns)

# Get statistics
stats = detector.get_pattern_statistics()

print(f"Total patterns found: {stats['total_patterns']}")
print(f"Pattern types: {stats['pattern_types']}")
print(f"Most common: {stats['most_common_type']}")
print(f"Duplicate groups: {stats['duplicate_groups']}")
print(f"Total duplicate instances: {stats['total_duplicate_instances']}")
```

---

## Integration with Athena

### With Semantic Memory

Store pattern information for future queries:

```python
from athena.manager import UnifiedMemoryManager

manager = UnifiedMemoryManager()

# Store pattern information
manager.remember({
    "type": "code_pattern",
    "pattern_type": "function",
    "name": "validate_email",
    "occurrences": 3,
    "files": ["src/validators.py", "src/utils.py", "tests/test_validators.py"],
})
```

### With Procedural Memory

Refactoring becomes a reusable procedure:

```python
# Extract refactoring procedure
refactoring_steps = [
    "1. Create shared utility module: src/validators/email_validator.py",
    "2. Move validate_email to shared module",
    "3. Update imports in src/validators.py",
    "4. Update imports in src/utils.py",
    "5. Run tests to verify behavior unchanged",
    "6. Remove duplicate definitions",
]

manager.learn_procedure({
    "name": "Refactor validate_email duplicates",
    "steps": refactoring_steps,
    "benefit": "Single source of truth for email validation"
})
```

### With Consolidation

Patterns are extracted during consolidation:

```python
# During consolidation, pattern statistics become semantic knowledge:
# "The codebase has 8 duplicate code groups, mostly in validation and utility functions"
# "High-priority refactoring: extract shared utility module for common operations"
```

---

## Best Practices

### 1. Regular Pattern Analysis

Analyze codebase periodically to catch emerging duplications:

```python
# Weekly analysis
def weekly_pattern_check():
    detector = PatternDetector()
    analysis = detector.analyze_codebase(["src/", "tests/"])

    if analysis["duplicate_groups"] > 5:
        alert("High duplication detected")
        for rec in analysis["recommendations"]:
            create_refactoring_issue(rec)
```

### 2. Proactive Consolidation

Use patterns as refactoring opportunities:

```python
for duplicate in analysis["duplicates"]:
    if duplicate.similarity_percentage > 90:
        # Near-identical code - high priority
        priority = "critical"
    elif duplicate.similarity_percentage > 80:
        # Very similar - medium priority
        priority = "high"
    else:
        # Somewhat similar - consider for future
        priority = "medium"

    create_refactoring_ticket(duplicate, priority)
```

### 3. Create Shared Utilities Early

When duplicates are found, create shared utilities:

```python
# Before: scattered duplicate code
# src/validators.py: validate_email(email)
# src/utils.py: validate_email(email)  # Different implementation!
# tests/test_email.py: validate_email(email)  # Yet another variant!

# After: single shared module
# src/core/validators.py: validate_email(email) - THE authoritative implementation
# src/validators.py: from src.core.validators import validate_email
# src/utils.py: from src.core.validators import validate_email
# tests/test_email.py: from src.core.validators import validate_email
```

### 4. Document Consolidation Decisions

When consolidating code, document the decision:

```python
# In src/core/validators.py:
"""
Email validation utilities.

This module consolidates email validation from:
- src/validators.py (original)
- src/utils.py (duplicate)
- tests/test_email.py (test variant)

All have been consolidated here with comprehensive testing.
Last updated: 2024-11-10
"""
```

### 5. Review Similarity Thresholds

Adjust thresholds based on your codebase:

```python
# High threshold (0.9+): Only very similar code
similar = detector.find_similar_functions(
    code, files, similarity_threshold=0.95
)

# Medium threshold (0.7-0.9): Reasonably similar
similar = detector.find_similar_functions(
    code, files, similarity_threshold=0.8
)

# Low threshold (0.5-0.7): Worth reviewing
similar = detector.find_similar_functions(
    code, files, similarity_threshold=0.6
)
```

---

## MCP Tool Integration

Strategy 3 is exposed via 3 MCP tools:

### 1. `detect_code_patterns`
Analyze codebase for patterns:
```json
{
  "codebase_files": ["src/", "tests/"]
}
```

### 2. `find_duplicate_code`
Find duplicate or similar code:
```json
{
  "code_snippet": "def validate(x): ...",
  "codebase_files": ["src/"]
}
```

### 3. `find_similar_functions`
Find similar functions in codebase:
```json
{
  "function_code": "def process(data): ...",
  "codebase_files": ["src/"],
  "similarity_threshold": 0.8
}
```

---

## Performance Characteristics

| Operation | Time | Memory | Notes |
|-----------|------|--------|-------|
| Extract patterns | O(n·m) | ~100KB per file | n=files, m=avg file size |
| Find duplicates | O(p²) | ~1KB per pattern | p=number of patterns |
| Find similar functions | O(p·f) | ~500B per comparison | p=patterns, f=files |
| Get statistics | O(p) | ~1KB | p=number of patterns |

**Optimization**: Results are cached. First run is slow, subsequent queries are fast.

---

## Code Normalization

The detector normalizes code for comparison:

```python
# Original code
def process(x):
    # Process the input
    result = x * 2  # Double it
    return result

# Normalized (for comparison)
def process x result x 2 return result

# This normalization handles:
# - Whitespace differences
# - Comment removal
# - Case normalization
# - Structural similarity
```

---

## Testing

The strategy includes comprehensive tests:

```bash
# Run Strategy 3 tests
pytest tests/unit/test_learning_pattern_detection.py -v

# Test coverage
# - Pattern extraction from files
# - Duplicate detection
# - Similar function finding
# - Code normalization
# - Refactoring suggestions
# - Multiple file analysis
```

---

## Common Patterns to Look For

### Validation Patterns
Spread across multiple files:
```python
if not data:
    return False
if len(data) < MIN_LENGTH:
    return False
if len(data) > MAX_LENGTH:
    return False
```

### Error Handling Patterns
Repeated try/except blocks:
```python
try:
    result = operation()
except Exception as e:
    logger.error(f"Failed: {e}")
    return None
```

### Transformation Patterns
Similar data transformations:
```python
result = {}
for item in items:
    result[item.id] = process(item)
return result
```

### Query Patterns
Similar database/API calls:
```python
try:
    response = client.get(endpoint)
    return response.json()
except ClientError:
    return {}
```

---

## Roadmap

### Phase 1 (Current)
- ✅ Function/class extraction via regex
- ✅ Duplicate detection by name and signature
- ✅ Logic pattern matching via normalization
- ✅ Refactoring recommendations

### Phase 2
- AST-based pattern analysis (more accurate)
- ML-based similarity scoring
- Import graph analysis (find over-coupled code)
- Automatic refactoring suggestions

### Phase 3
- Micro-clone detection (exact code duplicates)
- Semantic-aware duplicate detection
- Clone visualization and reporting
- Integration with IDEs for inline detection

---

## References

- **Related Strategies**:
  - Strategy 1: Error Diagnosis (find error handling duplicates)
  - Strategy 5: Git History (learn why duplicates were created)
  - Strategy 7: Synthesis (evaluate refactoring approaches)

- **Athena Layers**:
  - Episodic Memory: Stores pattern detection events
  - Semantic Memory: Queries for similar code patterns
  - Procedural Memory: Stores refactoring procedures

- **Research**:
  - Kamiya et al. 2002: "CCFinder: A Multi-Linguistic Token-based Code Clone Detection System"
  - Roy & Cordy 2007: "A Survey on Software Clone Detection Research"

---

**Status**: Production-ready
**Test Coverage**: 22/22 tests passing
**Last Updated**: November 2024
