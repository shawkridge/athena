---
name: memory-discoverer
description: Suggest relevant memories during work based on context
trigger: Model performing work or analysis, or user runs /memory-query, UserPromptSubmit, PostToolUse
confidence: 0.82
---

# Memory Discoverer Skill

Automatically suggests relevant memories during work without explicit user search requests.

## When I Invoke This

I detect:
- User submitting a prompt or question
- Claude using tools (Read, Write, Edit, Bash)
- Pattern shows related work happening
- Context suggests specific knowledge would help
- User working on task matching known domain

## What I Do

```
1. Analyze current context
   → Parse: Last user message or recent tool usage
   → Identify: Current domain (authentication, database, etc.)
   → Extract: Key concepts and entities
   → Check: Conversation history for continuity

2. Search for related memories
   → Call: smart_retrieve() with context analysis
   → Query: By domain, entity matches, semantic similarity
   → Retrieve: Top 5-10 candidate memories
   → Filter: Only relevant (confidence >0.6)

3. Rank candidates
   → Score: Relevance to current context
   → Weight: Recency (recent memories valued more)
   → Weight: Retrieval frequency (used often valued more)
   → Weight: User rating/usefulness
   → Rank: Top 2-3 highest confidence

4. Present suggestions
   → Show: Title/summary of memory
   → Show: Relevance score
   → Show: Quick action (view details, strengthen link)
   → Ask: "Would you like more context on this?"
```

## MCP Tools Used

- `smart_retrieve` - Find related memories using advanced RAG
- `recall` - Fallback semantic search
- `get_associations` - Find related concepts
- `search_graph` - Query knowledge graph for entities
- `record_event` - Track suggestion acceptance

## Configuration

```
CONFIDENCE_THRESHOLD: 0.60 (only suggest if >60% confident)
MAX_SUGGESTIONS: 3 (show max 3 at once, prevent overwhelm)
AUTO_TRIGGER: true (suggest without being asked)
TRIGGER_FREQUENCY: Every 10 tool operations or user message
RELEVANCE_WEIGHTS:
  semantic_similarity: 0.4
  domain_match: 0.3
  recency: 0.2
  usefulness: 0.1
```

## Example Invocation

```
User: /task-create "Implement OAuth2 for mobile clients"

Memory Discoverer analyzing context...
→ Domain detected: Authentication, Mobile, OAuth
→ Searching for related memories...
→ Found 12 relevant items

💡 SUGGESTED MEMORIES (ranked by relevance):

  1. JWT Token Implementation (score: 0.94)
     Memory ID: 456
     • JWT signing and validation patterns
     • Token refresh strategy
     • Error handling examples
     → View details: /memory-query ID:456

  2. OAuth2 Design Decision (score: 0.91)
     Memory ID: 789
     • OAuth2 vs JWT comparison
     • Security considerations
     • Implementation trade-offs
     → View details: /memory-query ID:789

  3. Mobile Authentication Security (score: 0.87)
     Memory ID: 234
     • Mobile-specific auth patterns
     • Token storage best practices
     • Network security considerations
     → View details: /memory-query ID:234

💬 Would any of these help with your OAuth2 implementation?
   (These suggestions auto-appear when working on related tasks)
```

## Expected Benefits

```
Discoverability: +30-50% increase in relevant memory retrieval
Context Relevance: +40-60% improvement in suggested relevance
Knowledge Reuse: Faster implementations via pattern reuse
Learning Reinforcement: Related memories strengthen connections
```

## Performance

- Per-context analysis: <100ms
- Memory retrieval: <1s (via smart_retrieve cache)
- Ranking: <500ms
- Total latency: <2s (non-blocking, async)

## Integration Points

- Works with: Any tool use (Read, Edit, Write, Bash, Glob, Grep)
- Works with: User prompts (UserPromptSubmit hook)
- Feeds into: consolidation-trigger (suggests memory connections to strengthen)
- Triggered by: PostToolUse (every 10 operations)
- Works with: `/memory-query` (extends search results with suggestions)

## Silent Mode

When confidence <0.75, operates silently:
- No user notification
- Still records suggestion acceptance
- Still strengthens associations
- User only sees high-confidence suggestions

## Limitations

- Cannot suggest memories for completely new domains
- Requires minimum 5+ existing memories to work effectively
- Performance degrades with very large memory databases (>50K)
- Context window size affects suggestion quality

## Related Commands

- `/memory-query` - Manual memory search (Memory Discoverer suggests from results)
- `/focus` - Set attention focus (Memory Discoverer filters by focus)
- `/consolidate` - Extract patterns (Memory Discoverer suggests consolidation targets)
- `/memory-health` - Check memory quality (Memory Discoverer suggests gaps to fill)

## Success Criteria

✓ Discovers 2-3 relevant memories without user request
✓ Suggestions ranked by relevance (highest confidence first)
✓ Confidence scores accurate (matches user judgment)
✓ No false positives (all suggestions actually useful)
✓ Performance <2s (not blocking work)
✓ Integration seamless (feels natural, not intrusive)
