---
description: Explore memory associations and knowledge graph relationships
group: Knowledge Graph & Associations
aliases: ["/graph", "/links", "/network", "/associations"]
---

# /connections

Navigate memory association networks, explore entity relationships, and strengthen knowledge links.

## Usage

```bash
/connections search "JWT"           # Find entity
/connections explore ID:456         # Explore relationships
/connections path ID:123 ID:789    # Find path between memories
/connections strengthen ID:456     # Strengthen association
```

## What It Shows

- **Associated Memories** - What's linked to selected item
- **Knowledge Graph** - Entities, relations, observations
- **Connection Strength** - Link weights and confidence
- **Paths** - Routes through association network
- **Clusters** - Related concept groups

## Example Output

```
CONNECTIONS EXPLORER
═══════════════════════════════════════════

Search Results: "JWT"
  Found: 23 items in knowledge graph

Primary Entity:
  📌 JWT Token Implementation (ID: 456)
     Type: Pattern
     Added: 2 weeks ago
     Confidence: 0.95

Associations (Strength: 1.0 = strongest):

Direct Connections:
  → Token Signing (strength: 0.95)
     └─ uses: RS256 algorithm
     └─ linked to: Security Architecture

  → Token Validation (strength: 0.92)
     └─ error handling: 3 related patterns
     └─ linked to: Middleware Design

  → Refresh Strategy (strength: 0.88)
     └─ decision: 1h token lifetime
     └─ linked to: Performance Optimization

Secondary Connections:
  → Authentication Flow (strength: 0.78)
  → Error Handling (strength: 0.75)
  → Testing Strategy (strength: 0.72)

Knowledge Graph View:
  [JWT Token Implementation]
    ├─ implements: [RS256 Signing]
    ├─ depends_on: [Cryptography Library]
    ├─ uses_pattern: [Token Validation]
    ├─ extends: [Authentication Flow]
    └─ contradicts: [HS256 Alternative]

Recommended Paths to Explore:
  1. JWT → RS256 → Cryptography (3 hops)
  2. JWT → Validation → Error Handling (3 hops)
  3. JWT → Refresh → Performance (4 hops)

Network Metrics:
  • Central Nodes (high connectivity):
    - Authentication Flow (8 connections)
    - Middleware Design (6 connections)
    - Error Handling (5 connections)

  • Isolated Clusters:
    - OAuth2 Integration (3 items, disconnected)
    - Performance Optimization (4 items, loosely connected)

Path Analysis (JWT → Performance):
  JWT Token Implementation
    → Refresh Strategy (strength: 0.88)
    → Cache Optimization (strength: 0.71)
    → Load Testing (strength: 0.64)
    → Performance Optimization (strength: 0.59)

  Distance: 4 hops, Confidence: 0.59

Recommendation:
  • Strengthen links to OAuth2 (isolated cluster)
  • Explore Performance Optimization connection
  • Review Token Validation contradiction with alternatives
```

## Commands

```bash
# Search and explore
/connections search "pattern"        # Find entity
/connections graph ENTITY            # Show relationship graph
/connections explore ID:456          # Full exploration

# Path finding
/connections path ID:123 ID:456     # Find path between items
/connections paths "topic"           # All paths from search

# Network analysis
/connections clusters               # Find concept clusters
/connections central                # Show high-connectivity nodes
/connections isolated               # Find disconnected items

# Strengthen links
/connections strengthen ID:456:0.1  # Increase strength by 0.1
/connections weaken ID:456          # Decrease strength
```

## Integration

Works with:
- `/memory-query` - Find items to explore
- `/consolidate` - Strengthen links during consolidation
- `/project-status` - Link to project entities
- `/reflect` - Analyze knowledge network

## Related Tools

- `get_associations` - Find associations
- `search_graph` - Query knowledge graph
- `find_memory_path` - Path finding
- `strengthen_association` - Increase link strength
- `create_relation` - Add relationships
- `create_entity` - Add entities

## Network Insights

| Pattern | Meaning | Action |
|---------|---------|--------|
| High connectivity | Central concept | Use for anchoring |
| Low strength | Weak connection | Strengthen or remove |
| Isolated clusters | Disconnected topics | Research bridges |
| Long paths | Distant concepts | Direct linking might help |

## Tips

1. Explore after research (new connections to old knowledge)
2. Strengthen useful associations (+0.1 at a time)
3. Find isolated clusters (missing links?)
4. Use for context switching (follow paths to related work)
5. Review network quarterly (maintenance)

## See Also

- `/memory-query` - Find items to explore
- `/consolidate` - Strengthen links
- `/project-status` - Link to project
