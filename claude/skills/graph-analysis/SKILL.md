---
name: graph-analysis
description: |
  When you need to understand knowledge graph structure through community detection.
  When finding bridge entities connecting different domains or analyzing graph organization.
  When graph-enhanced retrieval or community-based search would improve results.
---

# Graph Analysis Skill

Knowledge graph expert specializing in community detection, structure analysis, and GraphRAG synthesis.

## When to Use

- Need to understand knowledge graph organization
- Finding natural communities in the graph
- Identifying bridge entities between domains
- Graph-enhanced retrieval for better context
- Mapping expertise distribution
- Discovering knowledge gaps through graph analysis

## GraphRAG Approach

### Community Detection (Leiden Algorithm)
- Detect natural communities at multiple levels
- **Level 0 (Granular)** - Fine-grained communities
- **Level 1 (Intermediate)** - Mid-level clustering
- **Level 2 (Global)** - Broad organization
- Identify community hierarchies
- Map community relationships

### Community Characteristics
- Size and density
- Central entities
- Internal connections
- External bridges
- Topic/domain focus
- Growth patterns

## Available Tools

- **detect_graph_communities**: Find communities
- **get_community_details**: Community information
- **query_communities_by_level**: Browse by level
- **analyze_community_connectivity**: Relationship analysis
- **find_bridge_entities**: Connectors between communities

## Analysis Types

### Structural Analysis
- Network density
- Clustering coefficient
- Average path length
- Centrality measures
- Degree distribution
- Component connectivity

### Community Analysis
- Community size distribution
- Topic characterization
- Community quality
- Evolution over time
- Cross-community relationships

### Entity Analysis
- Centrality (how important)
- Betweenness (how central)
- Clustering (how connected)
- Community membership
- Bridge roles

## Knowledge Discovery

### Finding Expertise
"Where is our expertise in distributed systems?"
→ Find communities related to distributed systems
→ Identify central entities
→ Map expert knowledge

### Understanding Structure
"How is our knowledge organized?"
→ Detect communities
→ Show relationships
→ Visualize hierarchy

### Crossing Domains
"How do components connect?"
→ Find bridge entities
→ Show cross-community connections
→ Identify knowledge transfer points

## Graph-Enhanced Retrieval

### Community-Based Search
1. Identify relevant communities
2. Retrieve from community
3. Expand with related communities
4. Synthesize results
5. Provide context

### Context Enrichment
- Community context
- Related topics
- Expert entities
- Similar patterns
- Historical relationships

## Analysis Patterns

### Pattern 1: Expertise Mapping
"Map our architecture expertise"
→ Find architecture community, identify experts, show areas of strength/weakness

### Pattern 2: Knowledge Gaps
"Where are our knowledge gaps?"
→ Find isolated entities, identify weak communities, suggest learning focus

### Pattern 3: Domain Integration
"How connected are our domains?"
→ Find community bridges, measure connectivity, identify integration opportunities

## Quality Metrics

- **Modularity** - How well-defined are communities
- **Conductance** - How isolated communities are
- **Coverage** - Percentage of entities in communities
- **Balance** - Distribution of community sizes

## Example Use Cases

### Community Detection
"Find knowledge communities in the graph"
→ Runs Leiden algorithm, identifies 15 communities across 3 levels, characterizes each

### Bridge Analysis
"What entities connect consolidation and retrieval?"
→ Identifies bridge entities, analyzes connection strength, shows knowledge transfer paths

### Expertise Mapping
"Map our GraphRAG expertise"
→ Finds GraphRAG community, identifies central entities, shows related communities

## Best Practices

- **Explore Multiple Levels** - Use granular to global views
- **Follow Bridges** - Cross-community learning
- **Identify Experts** - Find central entities
- **Map Evolution** - Understand how graph grows
- **Combine Approaches** - Use with semantic search

Use graph analysis for powerful graph-aware knowledge discovery and synthesis.
