---
name: pattern-suggestion
description: |
  When encountering design problems, automatically suggest proven design patterns
  based on effectiveness tracking and similarity matching. Auto-triggers on problem descriptions.
  Uses filesystem API for token-efficient pattern discovery.
---

# Pattern Suggestion Skill

## What This Skill Does

Automatically suggests proven design patterns when you describe problems or implementation challenges. Learns from past effectiveness to recommend what actually works in your context.

## When to Use

Auto-triggers when conversation includes:
- Problem descriptions needing solutions
- "How should I..." or "What's the best way to..." questions
- Implementation uncertainty or multiple approaches
- Code organization challenges
- Component interaction design

**Keywords**: how to, best way, approach, solve, handle, manage, organize, design, pattern, strategy

## How It Works (Filesystem API Paradigm)

### Step 1: Analyze Problem
- Extract problem type from conversation
- Identify domain (e.g., data access, UI, concurrency)
- Categorize complexity
- Detect constraints mentioned

### Step 2: Discover Patterns
- Use `MemoryBridge.get_effective_patterns()` for proven patterns
- Query pattern library via filesystem API
- Filter by problem type and domain
- Progressive disclosure - summaries only

### Step 3: Match & Rank Locally
Execute matching in sandbox:
- **Similarity Scoring**: Match problem to pattern's problem statement
- **Effectiveness Filtering**: Prioritize patterns with high success rates
- **Context Relevance**: Consider project-specific usage history
- **Constraint Compatibility**: Check if pattern satisfies constraints

### Step 4: Return Suggestions
Return summary with:
- Top 3-5 matching patterns
- Effectiveness scores (from actual usage)
- Why each pattern fits
- Potential tradeoffs
- Implementation guidance pointers

## Returns (Summary Only)

```json
{
  "status": "success",
  "execution_method": "filesystem_api",
  "execution_time_ms": 95,

  "problem_summary": "Need to manage user sessions across multiple services",
  "problem_type": "distributed_state_management",
  "complexity": "medium",

  "suggested_patterns": [
    {
      "id": 42,
      "name": "Token-Based Authentication",
      "type": "architectural",
      "effectiveness_score": 0.91,
      "usage_count": 8,
      "relevance": 0.95,
      "why_this_fits": "Stateless tokens work well for distributed systems",
      "tradeoffs": [
        "+ No server-side session storage",
        "+ Scales horizontally easily",
        "- Token revocation is harder",
        "- Larger request size"
      ]
    },
    {
      "id": 18,
      "name": "Session Store Pattern",
      "type": "architectural",
      "effectiveness_score": 0.78,
      "usage_count": 5,
      "relevance": 0.82,
      "why_this_fits": "Centralized session management with Redis",
      "tradeoffs": [
        "+ Easy to revoke sessions",
        "+ Smaller request size",
        "- Requires session store infrastructure",
        "- Single point of failure risk"
      ]
    },
    {
      "id": 31,
      "name": "Distributed Cache Pattern",
      "type": "structural",
      "effectiveness_score": 0.85,
      "usage_count": 12,
      "relevance": 0.75,
      "why_this_fits": "Can cache session data across services",
      "tradeoffs": [
        "+ Improves performance significantly",
        "+ Reduces database load",
        "- Cache invalidation complexity",
        "- Consistency challenges"
      ]
    }
  ],

  "recommendation": "Token-Based Authentication recommended - highest effectiveness (91%) and best fit for distributed systems",

  "implementation_guidance": [
    "See ADR-12 for existing JWT implementation",
    "Pattern library has code examples for Token-Based Auth",
    "Consider hybrid approach: tokens + cache for performance"
  ],

  "related_adrs": [12, 15],
  "related_constraints": [5, 8],

  "note": "Get full pattern details via filesystem API for implementation"
}
```

## Token Efficiency

**Old Pattern** (load all patterns):
- Load full pattern library: 20K tokens
- Describe each pattern: 15K tokens
- User picks manually: N/A
- **Total: ~35K tokens**

**New Pattern** (auto-suggest with filtering):
- Analyze problem locally: 0 tokens (sandbox)
- Load pattern summaries: 200 tokens
- Match and rank locally: 0 tokens (sandbox)
- Return top suggestions: 300 tokens
- **Total: <500 tokens**

**Savings: 98.6% token reduction** 🎯

## Pattern Effectiveness Tracking

Patterns are ranked by **real effectiveness**, not theory:
- Success rate from actual usage in your projects
- Updated after each pattern application
- Failures decrease effectiveness score
- Proven patterns rise to top

**Example**:
```
Repository Pattern: 91% effective (10 uses, 9 successes)
Singleton Pattern: 45% effective (8 uses, 4 successes)
```

## Matching Algorithm

### High Relevance (0.8-1.0)
- Problem type exactly matches pattern's problem
- Domain is same (e.g., both data access)
- Constraints compatible
- High effectiveness in your context

### Medium Relevance (0.5-0.8)
- Problem type similar to pattern's problem
- Domain overlaps partially
- Some constraints need consideration
- Moderate effectiveness or limited usage

### Low Relevance (0.0-0.5)
- Different problem type
- Different domain
- Constraints conflict
- Low effectiveness or no usage history

## Examples

### Example 1: State Management Problem
**User**: "How should I handle application state that needs to be shared across multiple components?"

**Skill Auto-Triggers**:
- Detects state management problem
- Suggests: State Manager Pattern, Observer Pattern, Event Bus Pattern
- Ranks by effectiveness in your project
- Shows tradeoffs for each

### Example 2: API Design Question
**User**: "What's the best way to structure REST API endpoints?"

**Skill Auto-Triggers**:
- Identifies API design problem
- Suggests: Resource-Based Routing, Controller Pattern, Facade Pattern
- Shows effectiveness from past API implementations
- Links to relevant ADRs

### Example 3: Error Handling Challenge
**User**: "Need a better approach to handle errors across the system"

**Skill Auto-Triggers**:
- Recognizes error handling problem
- Suggests: Exception Middleware Pattern, Result Type Pattern, Error Boundary Pattern
- Ranks by success rate in error scenarios
- Notes constraint compatibility (logging, monitoring)

## Learning From Usage

The skill **learns and improves** over time:

1. **Pattern Applied**: You use suggested pattern
2. **Track Outcome**: System records success/failure
3. **Update Effectiveness**: Score adjusted based on result
4. **Better Suggestions**: Future suggestions reflect learning

**Example Evolution**:
```
Week 1: Suggests 5 patterns with unknown effectiveness
Week 4: Top 3 patterns have 85%+ effectiveness scores
Week 8: Suggestions are highly accurate, proven in your context
```

## Best Practices

1. **Trust High Effectiveness**: >80% means proven in your projects
2. **Consider Context**: Relevance + effectiveness together
3. **Document New Patterns**: Add patterns that work well for you
4. **Update After Use**: Mark success/failure to improve suggestions
5. **Review Tradeoffs**: No pattern is perfect - understand tradeoffs

## Integration with Architecture Layer

Uses filesystem API operations:
- `search_patterns()` - Find patterns by problem type
- `get_pattern_effectiveness()` - Get real success rates
- `get_pattern_details()` - Full pattern description (on demand)
- Local matching - all scoring in sandbox
- Summary-first - only top suggestions returned

## Pattern Types Available

- **Creational**: Factory, Builder, Singleton, Prototype
- **Structural**: Adapter, Facade, Proxy, Decorator, Composite
- **Behavioral**: Observer, Strategy, Command, State, Template Method
- **Architectural**: Layered, Microservices, Event-Driven, CQRS
- **Concurrency**: Lock, Read-Write Lock, Thread Pool, Producer-Consumer
- **Data Access**: Repository, DAO, Active Record, Unit of Work
- **Integration**: Gateway, Message Broker, API Gateway

## Automatic Activation

This skill is **auto-triggered** when conversation includes:
- Problem descriptions
- Questions about approaches
- Implementation uncertainty
- Design challenges
- "How to" or "best way" questions

No manual invocation needed - progressive activation based on context.

## Success Metrics

Track to improve over time:
- **Suggestion Accuracy**: % of times suggested pattern was used
- **Effectiveness Accuracy**: Correlation between predicted and actual success
- **Time to Solution**: Faster pattern discovery
- **Pattern Reuse**: Increased use of proven patterns
