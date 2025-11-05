---
category: skill
description: Navigate and explore knowledge graph associations, strengthen useful links
trigger: Model exploring related concepts, or user runs /connections command
confidence: 0.87
---

# Association Explorer Skill

Explores knowledge graph networks, finds connected concepts, and strengthens useful associations.

## When I Invoke This

I detect:
- User asks about related concepts
- Need to explore knowledge graph
- User runs `/connections` command
- Pattern shows weak links between related items
- Knowledge graph needs maintenance

## What I Do

```
1. Search for entity
   → Call: search_graph()
   → Find: Primary entity
   → Show: Direct connections
   → Identify: Related clusters

2. Explore relationships
   → Call: get_associations()
   → List: All connected items
   → Show: Link strength
   → Identify: Central concepts (hubs)

3. Find paths
   → Call: find_memory_path()
   → Path: Between two concepts
   → Distance: Number of hops
   → Strength: Confidence of connection

4. Strengthen useful links
   → Call: strengthen_association()
   → Increase: Links to related work
   → Decrease: Links to unrelated (optional)
   → Track: Link strength over time
```

## MCP Tools Used

- `search_graph` - Query knowledge graph
- `get_associations` - Find associations
- `find_memory_path` - Path finding
- `strengthen_association` - Increase link strength
- `create_relation` - Add new connections
- `add_observation` - Document findings

## Example Invocation

```
You: /connections search "JWT implementation"

Association Explorer analyzing...

Found: JWT Token Implementation (ID: 456)

Direct Associations:
  → Token Signing (0.95) - Strong
  → Token Validation (0.92) - Strong
  → Refresh Strategy (0.88) - Strong
  → Error Handling (0.75) - Medium
  → Performance (0.61) - Weak

Secondary Associations:
  → RS256 Algorithm (0.89)
  → Express Middleware (0.78)
  → Testing Strategy (0.72)

Network Map:
  [JWT] ──0.95── [Signing] ──0.82── [RS256]
     │
     ├─0.92─ [Validation]
     ├─0.88─ [Refresh]
     └─0.75─ [Error Handling]

High-Value Paths to Explore:
  1. JWT → Signing → RS256 (distance: 2, strength: 0.88)
  2. JWT → Validation → Error Handling (distance: 2, strength: 0.84)

Recommended Strengthening:
  • Weak link: JWT → Performance (0.61)
    → Reason: Performance testing is important
    → Strengthen by: +0.15
    → After: /connections strengthen ID:456:0.15

Network Maintenance:
  • Isolated clusters: OAuth2 (3 items, disconnected)
    → Recommendation: Link to JWT (missing integration doc)
  • Missing links: Refresh → Cache optimization
    → Recommendation: Create relation (performance impact)
```

## Success Criteria

✓ Associations found and explored
✓ Paths identified between concepts
✓ Useful links strengthened
✓ Network maintained and optimized

## Related Commands

- `/connections` - Explore knowledge graph
- `/consolidate` - Strengthen during consolidation
- `/memory-query` - Find concepts to explore

