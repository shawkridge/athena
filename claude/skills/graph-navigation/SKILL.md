---
name: graph-navigation
description: |
  Navigate knowledge graph relationships to understand dependencies and connections.
  Use when analyzing code impact, finding related concepts, or exploring entity relationships.
  Provides community detection, semantic paths, and relationship strength analysis.
---

# Graph Navigation Skill

## What This Skill Does

Explores your knowledge graph to understand how concepts, entities, and components relate to each other.

## When to Use

- Understanding code dependencies and change impacts
- Finding all related concepts for a topic
- Exploring entity relationships and connections
- Identifying concept communities and clusters

## How It Works

**Analysis Methods**:
- Entity relationships and direct connections
- Dependency chains (A → B → C)
- Semantic paths between distant entities
- Community detection (Leiden clustering)
- Bridge entity identification
- Temporal relationships

## What You Get

- Entity hierarchy and relationships
- Dependency chains showing impact
- Community memberships
- Semantic distance scores
- Bridge entities connecting communities
- Temporal evolution data

## Examples

- Explore "AuthenticationManager" → shows all its dependencies, users, and relationships
- Find path from "TokenExpiration" to "SecurityPolicy" → shows concept connections
- Identify communities in security domain → groups related security concepts

## Best Results

- Start with main entities: class names, module names, concept names
- Explore relationships to understand impact of changes
- Look for bridge entities to find unexpected connections

The graph-navigation skill activates automatically when exploring entity relationships.
