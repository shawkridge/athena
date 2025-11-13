# Strategy 5: Git History Analysis

## Overview

**Strategy 5** teaches AI to learn from architectural decisions and past patterns by analyzing git history. Rather than starting from scratch, the system understands why design decisions were made, what outcomes they had, and what lessons were learned.

**Core Philosophy**: *The codebase's git history is a record of all learning.* By understanding past decisions and their consequences, we can avoid repeating mistakes and apply proven patterns.

---

## How It Works

### 1. Commit Analysis

The `GitAnalyzer` examines git history to extract meaningful insights:

```python
from athena.learning.git_analyzer import get_git_analyzer

analyzer = get_git_analyzer()

# Analyze recent git history
analysis = analyzer.analyze_history(
    since_days=90,
    focus_keywords=["refactor", "migration"]
)

# Result:
# {
#     "analysis_timestamp": "2024-11-10T12:00:00",
#     "period_days": 90,
#     "total_commits": 256,
#     "decisions": [...],
#     "patterns": [...],
#     "lessons_learned": [...],
#     "insights": [...]
# }
```

### 2. Architectural Decision Extraction

The system identifies significant architectural decisions from commit messages:

```python
# Find architectural decisions
decisions = analyzer.find_architectural_decisions(
    patterns=["architecture", "refactor", "migration"]
)

# Each decision includes:
# - What decision was made
# - Who made it and when
# - Why it was made (rationale)
# - What the outcomes were
# - What was learned
```

### 3. Pattern Evolution Tracking

The system tracks how code patterns evolved over time:

```python
# Extract architectural decisions
decisions = analyzer.find_architectural_decisions()

# For each decision, understand:
# - When this pattern was introduced
# - How it evolved
# - Current status (active, deprecated, stable)
# - Lessons from its evolution
```

---

## Core Classes

### GitAnalyzer

Main class for git history analysis:

```python
class GitAnalyzer:
    def analyze_history(
        self,
        since_days: int = 90,
        focus_keywords: List[str] = None,
    ) -> Dict[str, Any]:
        """Analyze git history for decisions and patterns."""

    def find_architectural_decisions(
        self,
        patterns: List[str] = None,
    ) -> List[ArchitecturalDecision]:
        """Find significant architectural decisions."""

    def get_file_history(self, filepath: str) -> List[CommitInfo]:
        """Get commit history for specific file."""

    def blame_file(self, filepath: str) -> Dict[str, Any]:
        """Get blame information (who changed what and when)."""
```

### CommitInfo

Information about a git commit:

```python
@dataclass
class CommitInfo:
    sha: str                           # Git commit SHA
    author: str                        # Author name
    date: str                          # ISO timestamp
    message: str                       # Commit message
    files_changed: List[str]          # Files modified
    additions: int                     # Lines added
    deletions: int                     # Lines deleted
    is_merge: bool = False             # Is this a merge commit?
```

### ArchitecturalDecision

Represents a significant architectural decision:

```python
@dataclass
class ArchitecturalDecision:
    decision_id: str                   # Unique identifier
    title: str                         # What decision was made
    description: str                   # Details
    context: str                       # Problem being solved
    decision_maker: str                # Who decided
    date: str                          # When it was decided
    commit_sha: str                    # Git commit reference
    affected_files: List[str]         # Files involved
    rationale: str                     # Why this decision
    outcomes: List[str]                # What happened as a result
    lessons_learned: List[str]        # What we learned
```

### PatternEvolution

How a code pattern evolved:

```python
@dataclass
class PatternEvolution:
    pattern_name: str                  # Name of pattern
    first_appeared: str                # ISO timestamp
    last_modified: str                 # ISO timestamp
    commits: List[CommitInfo]         # Commits involved
    evolution_description: str         # How it evolved
    current_status: str                # active|deprecated|stable
```

### DecisionExtractor

Extracts decisions from commit messages:

```python
class DecisionExtractor:
    def extract_from_commit(
        self, commit_message: str
    ) -> Optional[Decision]:
        """Extract decision from commit message."""

    def extract_pattern_decisions(self) -> List[Decision]:
        """Extract common architectural decision patterns."""

    def learn_from_decisions(
        self, decisions: List[Decision]
    ) -> Dict[str, Any]:
        """Learn patterns from decisions."""
```

### DecisionLibrary

Query and learn from past decisions:

```python
class DecisionLibrary:
    def add_decision(self, decision_id: str, decision: Decision) -> None:
        """Add decision to library."""

    def query(self, keywords: List[str]) -> List[Decision]:
        """Query by keywords."""

    def get_similar_decisions(self, decision: Decision) -> List[Decision]:
        """Find similar past decisions."""

    def suggest_based_on_context(self, context: str) -> List[Decision]:
        """Get suggestions based on context."""
```

---

## Usage Examples

### Example 1: Understand Recent Architectural Changes

```python
analyzer = get_git_analyzer()

# What major architectural decisions were made in the last 6 months?
analysis = analyzer.analyze_history(since_days=180)

print(f"Total commits: {analysis['total_commits']}")
print(f"Architectural decisions: {len(analysis['decisions'])}")

for decision in analysis['decisions']:
    print(f"\n{decision['title']}")
    print(f"  Who: {decision['decision_maker']}")
    print(f"  When: {decision['date']}")
    print(f"  Why: {decision['rationale']}")
    print(f"  Outcome: {decision['outcomes'][0] if decision['outcomes'] else 'TBD'}")
```

### Example 2: Learn from Similar Past Decisions

```python
library = DecisionLibrary()

# Load historical decisions
historical_decisions = analyzer.find_architectural_decisions()
for i, decision in enumerate(historical_decisions):
    library.add_decision(f"decision_{i}", decision)

# Now facing a new decision: "Should we migrate to microservices?"
current_context = "Current monolith is hard to scale"

# Find similar past decisions
suggestions = library.suggest_based_on_context(current_context)

for suggestion in suggestions:
    print(f"Similar decision: {suggestion.title}")
    print(f"  Rationale: {suggestion.rationale}")
    print(f"  Outcomes: {suggestion.outcomes}")
    print(f"  Lessons: {suggestion.lessons_learned}")
```

### Example 3: Track Pattern Evolution

```python
# How has error handling evolved over time?
history = analyzer.get_file_history("src/errors/handlers.py")

print("Error handling evolution:")
for i, commit in enumerate(history[-5:]):  # Last 5 commits
    print(f"{i+1}. {commit.date}: {commit.message}")
    print(f"   +{commit.additions} -{commit.deletions} lines")
    print()

# This shows the evolution from:
# "Add try/except blocks" → "Create custom exceptions" → "Add error recovery"
```

### Example 4: Extract Lessons from Decision History

```python
extractor = DecisionExtractor()

# Load decisions from commits
decisions = []
for commit in analyzer._get_commits(since_days=90):
    decision = extractor.extract_from_commit(commit.message)
    if decision:
        decisions.append(decision)

# Learn from patterns
learnings = extractor.learn_from_decisions(decisions)

print(f"Common choices: {learnings['common_choices']}")
print(f"Successful patterns: {learnings['successful_patterns']}")
print(f"Failed patterns: {learnings['failed_patterns']}")
```

---

## Integration with Athena

### With Semantic Memory

Store architectural decisions for reference:

```python
from athena.manager import UnifiedMemoryManager

manager = UnifiedMemoryManager()

# Store architectural decision
decision = analyzer.find_architectural_decisions()[0]
manager.remember({
    "type": "architectural_decision",
    "title": decision.title,
    "rationale": decision.rationale,
    "outcomes": decision.outcomes,
    "lessons": decision.lessons_learned,
})
```

### With Prospective Memory

Use decisions as guidelines for future work:

```python
# If a decision says "avoid synchronous processing"
# Create a goal to monitor current code for sync processing
manager.set_goal({
    "name": "Ensure async-first architecture",
    "rationale": "Learned from past: sync processing limits scalability",
    "metric": "% of I/O operations that are async",
})
```

### With Consolidation

Architectural patterns are synthesized during consolidation:

```python
# During consolidation, extract:
# - "Our microservices pattern has evolved over 3 years"
# - "We've learned to separate read/write concerns"
# - "API versioning approach: gradual deprecation"
```

---

## Best Practices

### 1. Write Detailed Commit Messages

The more detailed your commits, the more the system can learn:

```bash
# ❌ Bad - minimal info
git commit -m "refactor"

# ✅ Good - clear decision rationale
git commit -m "refactor: Migrate to async/await

Problem: Callback-based async was becoming unmaintainable
Solution: Switch to Python 3.7+ async/await syntax
Rationale: Better syntax, easier error handling, matches team's style

Files affected:
- src/handlers.py (200 functions migrated)
- src/processing.py (50 functions migrated)

Outcomes:
- Code is 30% more readable
- Error handling is clearer
- Performance unchanged (good)

Lessons learned:
- Async/await takes 2-3 days to learn well
- Migration should be done per-module, not all at once
- Need comprehensive testing of exception propagation
"
```

### 2. Use Decision Keywords

Include decision keywords in commits so they're easier to find:

```bash
# Good keywords
git commit -m "architecture: Implement CQRS pattern"  # architecture
git commit -m "refactor: Extract shared validation"  # refactor
git commit -m "migration: Move to PostgreSQL"        # migration
git commit -m "design: Introduce dependency injection"  # design
```

### 3. Review Periodically

Make it a practice to review decisions:

```python
# Monthly review
def monthly_decision_review():
    analyzer = get_git_analyzer()

    decisions = analyzer.find_architectural_decisions()

    print("This month's architectural decisions:")
    for decision in decisions:
        print(f"- {decision.title}: {decision.rationale}")

    # Share with team for discussion
    create_discussion_thread(decisions)
```

### 4. Learn from Failed Decisions

Document when decisions didn't work out:

```bash
git commit -m "fix: Revert microservices experiment

This reverts 20e5a8f7

Rationale: Microservices added complexity without benefit
Lessons learned:
- Our scale (10M/day) doesn't justify microservices overhead
- Monolith with good module boundaries works better
- Team productivity increased after reverting
"
```

### 5. Create Decision Records

Consider ADR (Architecture Decision Record) format:

```bash
# ADR-001: Use PostgreSQL instead of MongoDB

## Status
Accepted (2024-01)

## Context
Need to choose database for user data storage

## Decision
Use PostgreSQL

## Rationale
- ACID guarantees required
- Complex queries needed
- Team expertise in SQL

## Consequences
- Better data integrity
- Learning curve for NoSQL team members
- More complex schema migrations

## Alternatives Considered
- MongoDB: Better horizontal scaling, but no ACID
- DynamoDB: Vendor lock-in risk
```

---

## MCP Tool Integration

Strategy 5 is exposed via 2 MCP tools:

### 1. `analyze_git_history`
Analyze git history for decisions and patterns:
```json
{
  "since_days": 90,
  "focus_keywords": ["refactor", "migration"]
}
```

### 2. `get_architectural_decisions`
Get specific architectural decisions:
```json
{
  "since_days": 90,
  "keywords": ["architecture", "design"]
}
```

---

## Performance Characteristics

| Operation | Time | Memory |
|-----------|------|--------|
| analyze_history (90 days) | 2-5s | ~10MB |
| find_architectural_decisions | 1-2s | ~5MB |
| get_file_history (single file) | 500ms | ~1MB |
| blame_file (single file) | 1-2s | ~2MB |
| extract_from_commit | <100ms | ~100KB |

**Optimization**: Results are cached. First run loads git data, subsequent queries are fast.

---

## Common Architectural Decisions

### 1. Architecture Style
- Monolith vs Microservices
- Layered vs Event-driven
- CQRS vs Traditional

### 2. Data Persistence
- SQL vs NoSQL
- Single database vs Polyglot
- Cache strategy (Redis, Memcached, CDN)

### 3. Async Patterns
- Callbacks vs Promises vs Async/await
- Queues vs Streams
- Pub/Sub vs Request/Reply

### 4. API Design
- REST vs GraphQL
- API versioning strategy
- Rate limiting approach

### 5. Deployment
- Monolith deployment vs CI/CD per service
- Blue/green vs Canary vs Rolling
- Containerization strategy

---

## Testing

The strategy includes comprehensive tests:

```bash
# Run Strategy 5 tests
pytest tests/unit/test_learning_git_history.py -v

# Test coverage
# - Git history analysis
# - Architectural decision extraction
# - Decision library queries
# - Pattern evolution tracking
# - Decision learning from patterns
```

---

## Roadmap

### Phase 1 (Current)
- ✅ Git history analysis
- ✅ Architectural decision extraction from commits
- ✅ Decision library and querying
- ✅ Pattern evolution tracking

### Phase 2
- Blame-based analysis (who changed what)
- Dependency evolution (how coupling changed)
- Code age analysis (code hotspots)
- Author expertise tracking

### Phase 3
- ML-based decision classification
- Decision impact analysis
- Team collaboration patterns
- Code review insights

### Phase 4
- ADR (Architecture Decision Record) integration
- Decision traceability to code
- Impact assessment for new decisions
- Predictive decision quality scoring

---

## References

- **Related Strategies**:
  - Strategy 1: Error Diagnosis (find why errors happened historically)
  - Strategy 3: Pattern Detection (find duplicate patterns over time)
  - Strategy 7: Synthesis (evaluate alternative decisions)

- **Athena Layers**:
  - Episodic Memory: Stores decision events
  - Semantic Memory: Stores decision rationales and outcomes
  - Procedural Memory: Stores decision processes

- **Resources**:
  - "Documenting Architecture Decisions" - Michael Nygard
  - "Git as a Time Machine" - Understanding version control history
  - Software Architecture in Practice - Bass, Clements, Kazman

---

## Examples in the Wild

### Kubernetes
- Original design decision: "Build as Google's internal system"
- Evolution: Learned from Borg/Omega, public cloud focus
- Decision: "Declarative API over imperative commands"
- Outcome: Highly successful, widely adopted

### React
- Original decision: "Virtual DOM for performance"
- Evolution: Hooks, Suspense, Concurrent rendering
- Pattern: Incremental adoption, backward compatibility
- Lesson: Good abstractions scale with feature needs

### PostgreSQL
- Original decision: "Academic research → production system"
- Evolution: ACID guarantees refined over 20 years
- Pattern: Conservative versioning, stability first
- Lesson: Reliability > features

---

**Status**: Production-ready
**Test Coverage**: 21/21 tests passing
**Last Updated**: November 2024
