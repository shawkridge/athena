# Senior Engineer Quick Guide - Planning Strategies

Use this to think like a senior engineer when building features or fixing bugs.

## Before You Code: 4-Step Research & Validation

### 1️⃣ Research (Strategy 2)
```python
from athena.research.research_orchestrator import execute_research, ResearchMode

# Research best practices
results = await execute_research(
    "your feature or problem",
    mode=ResearchMode.HYBRID,  # Real + mock fallback
    use_real=True,              # Try real web research
    use_mock=True               # Fallback if needed
)
```

**What it finds**:
- Official documentation and guides
- Open-source implementations
- Community discussions and patterns
- Academic research if applicable
- Company blog posts and tutorials

**Time**: ~5 seconds with parallel agents

---

### 2️⃣ Check Libraries (Strategy 4)
```python
from athena.analysis.library_analyzer import get_analyzer

analyzer = get_analyzer()
analysis = await analyzer.analyze_library(
    "requests",                    # Library name
    current_version="2.28.0",      # Your version
    check_vulnerabilities=True,
    check_updates=True
)

# Check for:
print(analysis.latest_version)              # Latest available
print(analysis.is_outdated)                 # Need to update?
print(analysis.capabilities.main_features)  # What it does
print(analysis.vulnerabilities)             # Security issues
print(analysis.dependencies)                # What it depends on
print(analysis.alternatives)                # Alternatives
```

**What it prevents**:
- Using deprecated/vulnerable versions
- Missing features available in latest
- Incompatible dependency combinations
- Architectural mistakes from library limits

**Time**: < 1 second per library

---

### 3️⃣ Prototype & Test (Strategy 6)
```python
from athena.prototyping.prototype_engine import get_prototype_engine

engine = get_prototype_engine()

# Create prototype
proto = engine.create_prototype(
    "Add async/await support to request handler",
    success_criteria=[
        "Handles 1000 concurrent requests",
        "Latency < 50ms",
        "No memory leaks after 1 hour"
    ]
)

# Add code
engine.add_artifact(
    proto.prototype_id,
    "code",
    """
async def handle_request(req):
    # Your prototype code here
    return await process(req)
    """
)

# Test it
results = await engine.execute_prototype(proto.prototype_id)
print(f"Success rate: {results['success_rate']:.0%}")

# Get feedback
feedback = await engine.validate_prototype(proto.prototype_id)
for issue in feedback:
    print(f"[{issue.severity}] {issue.description}")
    print(f"  → {issue.suggested_fix}")
```

**What it validates**:
- Idea actually works
- Success criteria can be met
- Major blockers identified early
- Rough performance characteristics

**Time**: ~10 seconds per prototype

---

### 4️⃣ Review Code (Strategy 8)
```python
from athena.mcp.handlers_review import review_code

# Review with all specialists
results = await review_code(
    code,
    reviewers=["style", "security", "architecture", "performance"]
)

# Check overall readiness
print(f"Quality Score: {results['overall_score']:.0%}")
print(f"Blocking Issues: {results['blocking_issues']}")
print(f"Ready to implement: {results['ready_for_implementation']}")

# See what each reviewer found
for review in results['reviews']:
    print(f"\n{review['reviewer']} ({review['domain']}):")
    print(f"  Score: {review['score']:.0%}")
    for issue in review['issues']:
        print(f"  [{issue['severity']}] {issue['title']}")
        if issue['suggestion']:
            print(f"    → {issue['suggestion']}")
```

**What each reviewer checks**:

| Reviewer | Checks |
|----------|--------|
| **Style** | Naming, formatting, docstrings, PEP 8 |
| **Security** | eval/exec, SQL injection, credentials, validation |
| **Architecture** | Function size, patterns, dependencies, cohesion |
| **Performance** | N+1 queries, blocking ops, efficiency |
| **Accessibility** | Error messages, i18n, usability, help |

**Critical Score for Shipping**: > 70% AND zero critical issues

**Time**: < 2 seconds to review

---

## Full Workflow Example

```python
import asyncio
from athena.research.research_orchestrator import execute_research, ResearchMode
from athena.analysis.library_analyzer import get_analyzer
from athena.prototyping.prototype_engine import get_prototype_engine
from athena.mcp.handlers_review import review_code

async def implement_feature(feature_idea: str, code_snippet: str):
    print(f"🚀 Implementing: {feature_idea}\n")

    # Step 1: Research
    print("📚 Researching best practices...")
    research = await execute_research(feature_idea, mode=ResearchMode.HYBRID)
    print(f"   Found {sum(len(f) for f in research.values())} sources")

    # Step 2: Check dependencies
    print("\n📦 Analyzing dependencies...")
    analyzer = get_analyzer()
    # (Check any libs used)

    # Step 3: Prototype
    print("\n🧪 Creating prototype...")
    engine = get_prototype_engine()
    proto = engine.create_prototype(
        feature_idea,
        success_criteria=["Compiles", "Passes basic tests"]
    )
    engine.add_artifact(proto.prototype_id, "code", code_snippet)

    results = await engine.execute_prototype(proto.prototype_id)
    print(f"   Success rate: {results['success_rate']:.0%}")

    feedback = await engine.validate_prototype(proto.prototype_id)
    if feedback:
        for issue in feedback:
            print(f"   [{issue.severity}] {issue.description}")
            if issue.suggested_fix:
                engine.refine_prototype(proto.prototype_id, [issue.suggested_fix])

    # Step 4: Review
    print("\n🔍 Reviewing code...")
    review = await review_code(code_snippet)
    print(f"   Overall score: {review['overall_score']:.0%}")
    print(f"   Blocking issues: {review['blocking_issues']}")

    if review['ready_for_implementation']:
        print("\n✅ Ready to ship!")
        engine.promote_to_implementation(proto.prototype_id, {"status": "approved"})
    else:
        print("\n❌ Need fixes before shipping")
        for review_result in review['reviews']:
            for issue in review_result['issues']:
                if issue['severity'] == 'critical':
                    print(f"   Fix: {issue['suggestion']}")

# Usage
asyncio.run(implement_feature(
    "Add caching to database queries",
    """
def get_user(user_id):
    sql_query = f"SELECT * FROM users WHERE id = {user_id}"
    return execute(sql_query)
    """
))
```

---

## MCP Tool Reference

### Research
- `research_topic(topic, mode, use_real, use_mock)` - General research
- `research_library(lib, type)` - Library-specific research
- `research_pattern(pattern, context)` - Design pattern research
- `get_research_agents()` - List available agents

### Analysis
- `analyze_library(name, version)` - Full library analysis
- `analyze_requirements(file)` - Analyze requirements.txt
- `check_library_compatibility(lib1, lib2)` - Check conflicts
- `get_library_alternatives(lib)` - Find alternatives

### Prototyping
- `create_prototype(idea, criteria)` - Start prototype
- `add_artifact(id, type, content)` - Add code/design
- `execute_prototype(id)` - Run prototype
- `validate_prototype(id)` - Get feedback
- `refine_prototype(id, improvements)` - Improve
- `promote_prototype(id, plan)` - Move to impl
- `list_prototypes(phase)` - Browse prototypes

### Review
- `review_code(code, reviewers)` - Multi-reviewer review
- `review_with_reviewer(code, type)` - Single reviewer
- `get_available_reviewers()` - List reviewers
- `review_and_suggest_fixes(code, type)` - Get fixes

---

## Decision Tree: When to Use What

```
Feature request comes in
│
├─→ "What are best practices?"
│   └─→ research_topic()
│
├─→ "Should we use library X?"
│   ├─→ analyze_library(X)
│   └─→ check_library_compatibility(X, Y)
│
├─→ "Will this approach work?"
│   └─→ create_prototype() → execute_prototype() → validate_prototype()
│
└─→ "Is code ready to merge?"
    └─→ review_code() → fix_issues() → ready!
```

---

## Modes & Options

### Research Modes
- `HYBRID` (default) - Try real APIs, fallback to mock
- `REAL_FIRST` - Real APIs with mock fallback
- `MOCK_ONLY` - Mock only (for testing)
- `OFFLINE` - Mock only, no network attempts

### Review Domains
- `style` - Code style and formatting
- `security` - Security vulnerabilities
- `architecture` - Design and structure
- `performance` - Performance optimization
- `accessibility` - Usability and accessibility

### Prototype Phases
1. `conception` - Plan and define
2. `generation` - Write artifacts
3. `execution` - Run and test
4. `validation` - Collect feedback
5. `refinement` - Improve
6. `promotion` - Move to implementation

---

## Tips for Senior Engineer Mode

✅ **DO**:
- Research before implementing
- Check library constraints early
- Prototype risky ideas
- Review code before merging
- Learn from feedback
- Document decisions

❌ **DON'T**:
- Assume best practices without research
- Ignore library version issues
- Commit to architecture without testing
- Skip code review
- Hardcode without considering i18n
- Use eval/exec ever

---

## Performance

| Operation | Time |
|-----------|------|
| Research | ~5 sec (parallel) |
| Library analysis | <1 sec |
| Prototype execution | ~2 sec |
| Code review | <2 sec |
| **Total pipeline** | **~10 sec** |

All operations are non-blocking and can run in parallel.

---

**Remember**: A senior engineer thinks before coding. These tools automate that thinking.
