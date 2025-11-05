---
description: Navigate and strengthen Hebbian association network between memories
allowed-tools: mcp__memory__get_associations, mcp__memory__strengthen_association, mcp__memory__find_memory_path
group: memory-management
---

# /associations - Hebbian Association Network Navigator

## Overview

Navigate the Hebbian association network connecting your memories. View related memories, discover knowledge clusters, strengthen important links, and trace memory paths. This command exposes the emergent learning network that forms from your retrieval and memory interactions.

## Usage

```
/associations <memory_id> [--depth 2] [--strengthen] [--find-path <target_id>] [--graph] [--json]
```

## Commands

### View Memory Associations (Default)
```
/associations 42
```

Shows all memories associated with memory ID 42, organized by association strength.

**Example Output:**
```
═══════════════════════════════════════════════════════════════
ASSOCIATIONS FOR MEMORY #42: "LLM memory architectures"
═══════════════════════════════════════════════════════════════

Association Strength Score = 0.68 (strong cluster)

TIER 1 - Direct Associations (Distance 1):
  [0.92] #156: "Episodic memory consolidation"
         Strength: 0.92 (very strong)
         Last accessed: 2m ago
         Type: Semantic memory

  [0.87] #201: "Working memory capacity models"
         Strength: 0.87 (very strong)
         Last accessed: 15m ago
         Type: Semantic memory

  [0.71] #089: "Baddeley's WM model"
         Strength: 0.71 (strong)
         Last accessed: 2h ago
         Type: Semantic memory

  [0.54] #312: "RAG vs fine-tuning"
         Strength: 0.54 (moderate)
         Last accessed: 12h ago
         Type: Decision

TIER 2 - Secondary Associations (Distance 2):
  [0.68] #445: "Knowledge graph design"
         Path: #42 → #156 → #445

  [0.61] #523: "Consolidation algorithms"
         Path: #42 → #201 → #523

  [0.45] #178: "Retrieval effectiveness metrics"
         Path: #42 → #089 → #178

CLUSTER ANALYSIS:
  Primary cluster: Memory systems (5 memories)
  Bridge entity: "Episodic memory consolidation" (#156)
  Cluster strength: 0.78 (coherent)

SUGGESTIONS:
  ✓ #156 is a bridge entity - highly connected (consider pinning)
  ✓ Strengthen link #42→#312 to connect RAG research
  ✓ Consider researching domain: "Fine-tuning vs RAG comparison"
```

### Specify Search Depth
```
/associations 42 --depth 3
```

Control how many association "hops" to show:
- `--depth 1`: Direct associations only
- `--depth 2`: One level of secondary associations (default)
- `--depth 3`: Deep exploration (slower, comprehensive)

### Strengthen Association
```
/associations 42 --strengthen 156
```

Increase association strength between memory 42 and memory 156. Useful after productive co-retrieval or when you discover important links.

**Example:**
```
/associations 42 --strengthen 156 --amount 0.15

Strengthened association #42 ↔ #156:
  Previous strength: 0.92
  New strength: 0.98 (very strong)

This link is now highly prioritized for co-retrieval.
```

### Find Memory Path
```
/associations 42 --find-path 312
```

Trace the shortest semantic path between two memories. Helps discover how different domains connect.

**Example Output:**
```
MEMORY PATH: #42 → #312

Shortest path (2 hops):
  #42 (LLM memory architectures)
    ↓ [strength: 0.68]
  #201 (Working memory models)
    ↓ [strength: 0.74]
  #312 (RAG vs fine-tuning)

Alternative paths:
  Path 2 (3 hops): #42 → #089 → #445 → #312
  Path 3 (4 hops): #42 → #156 → #523 → #178 → #312

Strongest direct link: 0.68
Overall path coherence: 0.70 (good)

INSIGHT: These domains share memory systems context.
Consider: How do RAG and working memory relate?
```

### Visualize Association Graph
```
/associations 42 --graph [--format ascii|json]
```

Show visual representation of association network around a memory.

**ASCII Graph:**
```
                      #156 (episodic consolidation) ──0.92──┐
                         │                                    │
                      0.78│                                0.68
                         │                                    ↓
#42 ─────0.87───→ #201 (WM models) ─────0.74──→ #312 (RAG)
 │                      │
 └──0.71─→ #089 (Baddeley) ──0.65──→ #445 (KG design)
```

**JSON Graph:**
```json
{
  "center_memory": {
    "id": 42,
    "content": "LLM memory architectures",
    "type": "semantic"
  },
  "nodes": [
    {"id": 156, "content": "Episodic consolidation", "strength": 0.92},
    {"id": 201, "content": "WM models", "strength": 0.87}
  ],
  "edges": [
    {"from": 42, "to": 156, "strength": 0.92},
    {"from": 42, "to": 201, "strength": 0.87}
  ]
}
```

### Full JSON Output
```
/associations 42 --json
```

Structured output for programmatic analysis:
```json
{
  "memory_id": 42,
  "associations": [
    {
      "target_id": 156,
      "strength": 0.92,
      "last_accessed": "2025-10-24T14:32:00Z",
      "type": "semantic",
      "path_distance": 1,
      "content_preview": "Episodic memory consolidation"
    }
  ],
  "cluster_analysis": {
    "primary_cluster": "Memory systems",
    "cluster_strength": 0.78,
    "bridge_entities": [156]
  }
}
```

## Hebbian Learning Mechanics

Associations strengthen through:

1. **Co-retrieval:** When two memories retrieved together
2. **Temporal Proximity:** Recent interactions strengthen links
3. **Semantic Similarity:** Related content naturally associates
4. **Manual Strengthening:** Explicit link enhancement (you)
5. **Consolidation:** Sleep-like consolidation discovers new links

**Formula:**
```
Strength(A, B) = 0.6 × co_retrieval_count
                + 0.3 × semantic_similarity
                + 0.1 × recency_weight
```

## Key Insights

### Bridge Entities
High-degree connecting memories that link different knowledge domains.

**Indicator:** Appears in multiple association paths.

**Value:** Critical for cross-domain knowledge transfer.

**Action:** Consider pinning bridge entities to long-term focus.

### Clustering
Groups of highly associated memories representing coherent knowledge domains.

**Strength:** How tightly clustered (0.0-1.0)
- **0.8+**: Coherent, well-researched domain
- **0.5-0.8**: Related but diverse
- **<0.5**: Loosely connected

### Association Decay
Links weaken if memories not co-accessed.

**Decay rate:** Exponential, ~2-4 weeks to 50% strength

**Solution:** Regular co-retrieval or manual strengthening.

## Advanced Usage

### Find All Bridge Entities
```
/associations --find-bridges [--min-degree 3]
```

Identify memories that connect multiple clusters. Useful for discovering integrative knowledge.

### Suggest Novel Connections
```
/associations 42 --suggest-connections [--domains 3]
```

AI-powered suggestions for memory pairings that *should* be connected but aren't yet.

**Example:**
```
SUGGESTED CONNECTIONS for #42:

  Recommendation 1: Connect to #678 (Temporal dynamics)
    Reason: Both involve sequential processing
    Expected strength: 0.65

  Recommendation 2: Connect to #234 (Attention mechanisms)
    Reason: Both critical for LLM behavior
    Expected strength: 0.72
```

### Strengthen Entire Cluster
```
/associations 42 --strengthen-cluster --amount 0.10
```

Increase strength of all associations within a cluster. Useful after deep learning session.

### Detect Contradictions
```
/associations 42 --check-contradictions
```

Find associated memories with conflicting information.

## Integration with Skills

The **association-learner** skill automatically:
- Strengthens co-retrieved memories
- Detects new bridge entities
- Warns about weakening links
- Suggests manual strengthening

Manual use of `/associations` lets you guide this process.

## Tips & Best Practices

### 1. Regular Network Exploration
Periodically explore associations to understand your knowledge structure:
```
/associations 42 --graph
```

### 2. Strengthen Key Bridges
After productive sessions, strengthen bridge entities:
```
/associations 42 --strengthen 156 --amount 0.15
```

### 3. Monitor Cluster Coherence
Check cluster strength periodically - declining strength suggests decay:
```
/associations 42 --depth 2
```

### 4. Use Path Finding for Insights
Discover cross-domain connections:
```
/associations 42 --find-path 312
```

### 5. Combine with Memory-Query
After finding associations, deep-dive with:
```
/memory-query "association context for #42"
```

## Performance Characteristics

| Operation | Time | Complexity |
|-----------|------|-----------|
| View associations | <50ms | O(n) |
| Find shortest path | 100-500ms | O(n²) |
| Strengthen link | <10ms | O(1) |
| Find bridges | 500-2000ms | O(n²) |
| Detect contradictions | 1-5s | O(n³) |

## Related Commands

- `/memory-query` - Search memories; shows related findings
- `/consolidate` - Consolidation discovers new associations
- `/memory-health` - Includes association network health
- `/focus` - Can focus on association clusters

## See Also

- **Hebbian Learning:** "Neurons that fire together, wire together"
- **Association Networks:** Graph-based knowledge representation
- **Bridge Entities:** High-betweenness nodes in semantic networks
- **Co-retrieval Strengthening:** Implicit memory phenomena in cognitive science
