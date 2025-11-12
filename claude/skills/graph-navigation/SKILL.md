---
name: graph-navigation
description: |
  Graph navigation using filesystem API paradigm (discover → read → execute → summarize).
  Explore knowledge graph relationships, dependencies, communities, and semantic paths.
  Executes locally, returns summaries only (99%+ token reduction).
---

# Graph Navigation Skill (Filesystem API Edition)

Explore knowledge graph relationships to understand dependencies, connections, and community structures.

## What This Skill Does

Navigates your knowledge graph to understand how concepts, entities, and components relate to each other, revealing dependencies, communities, and semantic paths.

## When to Use

- Understanding code dependencies and change impacts
- Finding all related concepts for a topic
- Exploring entity relationships and connections
- Identifying concept communities and clusters
- Discovering bridge entities and unexpected connections
- Analyzing temporal evolution of entities

## How It Works (Filesystem API Paradigm)

### Step 1: Discover
- Use `adapter.list_operations_in_layer("graph")`
- Discover available graph operations
- Show what navigation, analysis, and community detection operations exist

### Step 2: Select Analysis Type
- Determine query type (entity exploration, path finding, community detection)
- Identify start entities and relationships to follow
- Prepare analysis parameters

### Step 3: Execute Locally
- Use `adapter.execute_operation("graph", operation, args)`
- Graph traversal and analysis happens in sandbox (~150-300ms)
- Leiden community detection runs locally
- Semantic path finding and scoring
- No data loaded into context

### Step 4: Return Summary
- Entity relationships discovered
- Community memberships and characteristics
- Dependency chains and impact scores
- Bridge entities and their connecting roles
- Semantic distances and path strengths
- Temporal evolution patterns

## Analysis Methods

**Direct Exploration**:
- Entity relationships and direct connections
- Incoming and outgoing relationship types
- Entity properties and metadata

**Dependency Analysis**:
- Dependency chains (A → B → C)
- Impact scoring for change analysis
- Cyclic dependency detection
- Bottleneck identification

**Semantic Paths**:
- Paths between distant entities
- Relationship type sequences
- Strength and confidence scores
- Alternative path discovery

**Community Detection**:
- Leiden clustering algorithm
- Community memberships
- Within-community cohesion
- Between-community bridges

**Bridge Entity Analysis**:
- Entities connecting communities
- Cross-cutting concerns
- Integration points
- Influence scores

## Returns (Summary Only)

```json
{
  "status": "success",
  "execution_method": "filesystem_api",
  "execution_time_ms": 245,

  "query_entity": "AuthenticationManager",
  "analysis_type": "full_exploration",

  "entity_summary": {
    "id": 42,
    "name": "AuthenticationManager",
    "type": "class",
    "properties": {
      "module": "security",
      "responsibility": "Token generation and validation"
    }
  },

  "direct_relationships": {
    "total": 23,
    "incoming": 8,
    "outgoing": 15,
    "types": {
      "depends_on": 7,
      "used_by": 8,
      "extends": 1,
      "implements": 5,
      "related_to": 2
    }
  },

  "related_entities": [
    {
      "id": 50,
      "name": "TokenValidator",
      "type": "class",
      "relationship": "depends_on",
      "strength": 0.95
    },
    {
      "id": 51,
      "name": "SecurityPolicy",
      "type": "concept",
      "relationship": "implements",
      "strength": 0.88
    },
    {
      "id": 48,
      "name": "UserService",
      "type": "class",
      "relationship": "used_by",
      "strength": 0.92
    }
  ],

  "dependency_chains": [
    {
      "chain": ["AuthenticationManager", "TokenValidator", "CryptoService"],
      "length": 3,
      "impact_score": 0.87,
      "breakpoint_risk": "low"
    },
    {
      "chain": ["AuthenticationManager", "DatabaseAdapter", "QueryExecutor"],
      "length": 3,
      "impact_score": 0.79,
      "breakpoint_risk": "medium"
    }
  ],

  "communities": {
    "detected": 4,
    "memberships": [
      {
        "community_id": 1,
        "name": "Security subsystem",
        "size": 12,
        "cohesion": 0.92,
        "role": "core"
      },
      {
        "community_id": 2,
        "name": "Data access",
        "size": 8,
        "cohesion": 0.85,
        "role": "supporting"
      }
    ],
    "bridge_entities": [
      {
        "id": 45,
        "name": "ConfigManager",
        "bridges": [1, 2],
        "influence": 0.78
      }
    ]
  },

  "semantic_paths": [
    {
      "from": "AuthenticationManager",
      "to": "SecurityPolicy",
      "paths": [
        {
          "path": ["AuthenticationManager", "TokenValidator", "SecurityPolicy"],
          "strength": 0.91,
          "relationship_types": ["implements", "validates_against"]
        }
      ],
      "shortest_distance": 2,
      "semantic_similarity": 0.89
    }
  ],

  "impact_analysis": {
    "if_modified": {
      "directly_affected": 8,
      "transitively_affected": 15,
      "total_impact_scope": 23,
      "impact_percentage": 34.8
    },
    "risk_assessment": "medium"
  },

  "temporal_evolution": {
    "first_appearance": "2025-06-15",
    "last_modified": "2025-11-10",
    "relationship_changes": 5,
    "expansion_rate": "gradual",
    "stability": "stable"
  },

  "recommendations": [
    "ConfigManager bridges Security and Data Access communities (key integration point)",
    "TokenValidator is critical dependency - 15 entities transitively depend on it",
    "3 cyclic relationships detected - may indicate architecture issues",
    "SecurityPolicy relationship strengthening - more entities implementing it recently"
  ],

  "note": "Call adapter.get_detail('graph', 'entity', 42) for full entity analysis"
}
```

## Graph Operations

1. **explore_entity**: Full exploration of single entity
2. **find_path**: Shortest and semantic paths between entities
3. **detect_communities**: Leiden clustering and community analysis
4. **analyze_dependencies**: Dependency chains and impact analysis
5. **find_bridges**: Cross-community bridge entities
6. **measure_connectivity**: Network metrics and centrality

## Token Efficiency
Old: 120K tokens | New: <350 tokens | **Savings: 99%**

## Examples

### Basic Entity Exploration

```python
# Discover available graph operations
adapter.list_operations_in_layer("graph")
# Returns: ['explore_entity', 'find_path', 'detect_communities', 'analyze_dependencies']

# Explore a specific entity
result = adapter.execute_operation(
    "graph",
    "explore_entity",
    {"entity_name": "AuthenticationManager"}
)

# Review relationships
print(f"Entity: {result['entity_summary']['name']}")
print(f"Relationships: {result['direct_relationships']['total']}")

# Check for high-risk dependencies
for chain in result['dependency_chains']:
    if chain['breakpoint_risk'] == 'high':
        print(f"HIGH RISK: {chain['chain']}")
```

### Finding Semantic Paths

```python
# Find paths between concepts
result = adapter.execute_operation(
    "graph",
    "find_path",
    {
        "from_entity": "TokenExpiration",
        "to_entity": "SecurityPolicy",
        "max_distance": 5
    }
)

for path_obj in result['semantic_paths']:
    for path in path_obj['paths']:
        print(f"Path: {' → '.join(path['path'])}")
        print(f"Strength: {path['strength']:.2f}")
```

### Community Detection

```python
# Detect knowledge communities
result = adapter.execute_operation(
    "graph",
    "detect_communities",
    {"algorithm": "leiden", "min_community_size": 5}
)

print(f"Communities found: {result['communities']['detected']}")

# Find bridge entities
for bridge in result['communities']['bridge_entities']:
    print(f"Bridge: {bridge['name']} connects communities {bridge['bridges']}")
```

### Impact Analysis

```python
# Analyze impact of changes
result = adapter.execute_operation(
    "graph",
    "analyze_dependencies",
    {"entity_id": 42, "depth": 3}
)

impact = result['impact_analysis']['if_modified']
print(f"Direct impact: {impact['directly_affected']} entities")
print(f"Transitive impact: {impact['transitively_affected']} entities")
print(f"Risk: {result['impact_analysis']['risk_assessment']}")
```

### Finding Critical Dependencies

```python
# Find most central entities
result = adapter.execute_operation(
    "graph",
    "measure_connectivity",
    {"metric": "centrality", "top_k": 5}
)

for entity in result['top_entities']:
    print(f"{entity['name']}: centrality {entity['centrality']:.2f}")
```

## Implementation Notes

Demonstrates filesystem API paradigm for knowledge graph exploration. This skill:
- Discovers available graph operations via filesystem
- Navigates knowledge graph relationships and communities
- Analyzes dependencies and change impacts
- Returns only summary metrics (entity counts, relationship strengths, IDs)
- Supports drill-down for full entity details via `adapter.get_detail()`
- Uses Leiden algorithm for community detection
- Identifies bridge entities and critical dependencies
- Tracks temporal evolution of relationships
