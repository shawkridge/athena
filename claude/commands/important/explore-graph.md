---
description: Navigate knowledge graph relationships to understand dependencies and connections
argument-hint: "Entity name or concept to explore"
---

# Explore Graph

Navigate the knowledge graph to understand relationships, dependencies, and connections between concepts.

Usage: `/explore-graph "concept name"` or `/explore-graph "Entity A" "Entity B"`

Features:
- **Entity Relationships**: Explore how concepts are related
- **Dependency Chains**: Trace dependencies and impact
- **Community Detection**: Leiden clustering to find natural concept groups
- **Semantic Paths**: Find connections between distant entities
- **Observation Context**: View contextual observations on entities

Returns:
- Entity hierarchy and direct relationships
- Dependency chains (A depends on B depends on C)
- Community memberships and bridge entities
- Semantic distance and relationship strength
- Path suggestions between entities
- Related contexts and observations
- Temporal relationships (what changed when)

Example outputs:
```
Entity: AuthenticationSystem
├─ Implements: Security Policy
├─ Uses: JWT Token Library
├─ DependsOn: Database User Table
├─ RelatesTo: SessionManagement
└─ Observations:
   - Last updated 2 weeks ago
   - Used by 3 API endpoints
   - Has 2 known issues

Community: "Security Infrastructure"
├─ Entities: AuthenticationSystem, SessionManagement, Encryption
├─ Density: 0.87 (tightly connected)
└─ Bridge Entities: SecurityAuditor (connects to PolicyManagement)
```

The knowledge-explorer agent autonomously invokes this for impact analysis and relationship discovery.
